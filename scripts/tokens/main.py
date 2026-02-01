import json
from collections import defaultdict

import pathlib
from typing import Dict, List, Any

from .mtgjson_parser import MtgjsonParser
from .mtgjson_to_tcgplayer_mapper import MtgjsonToTcgplayerMapper
from .tcgplayer_provider import TcgplayerProvider
from .tcgplayer_token_parser import TcgplayerTokenParser

TCGPLAYER_REFERRAL_URL: str = (
    "https://partner.tcgplayer.com/c/4948039/1780961/21018?subId1=api&u="
    "https%3A%2F%2Fwww.tcgplayer.com%2Fproduct%2F{}%3Fpage%3D1"
)


def import_overrides() -> Dict[str, List[Dict[str, Any]]]:
    """
    Import overrides for tokens. This will overwrite the MTGJSON UUIDs with
    whatever is in the data/token_manual_overrides.json file.

    That file should have the following format:
    {
        "MTGJSON_UUID_1": [{
          "parentSetCode": "ABC",
          "identifiers": {
            "tcgplayerProductId": "1234567890"
          },
          "tokenParts": [
            {
              "uuid": "MTGJSON_UUID_1"
            },
            {
              "uuid": "MTGJSON_UUID_2",
              "faceAttributes": ["attr1", "attr2"]
            }
          ]
        }],
        ...
    }

    :returns A properly formatted dict that can be indexed by parentSetCode to get overrides
    """
    # Load overrides into memory
    with pathlib.Path("data/token_manual_overrides.json").open("r") as fp:
        data = json.load(fp)

    # Expand overrides with relevant details
    overrides = defaultdict(lambda: defaultdict(list))
    for mtgjson_uuid, token_entries in data.items():
        for token_entry in token_entries:
            token_entry["purchaseUrls"] = {
                "tcgplayer": TCGPLAYER_REFERRAL_URL.format(
                    token_entry["identifiers"]["tcgplayerProductId"]
                )
            }
            # Remove the helper component
            set_code = token_entry["parentSetCode"]
            del token_entry["parentSetCode"]
            overrides[set_code][mtgjson_uuid].append(token_entry)

    return overrides


def tcgplayer_token_to_mtgjson_token_products_entry(
    tcgplayer_token: Dict[str, Any],
) -> Dict[str, Any]:
    return {
        "identifiers": {
            "tcgplayerProductId": str(tcgplayer_token["productId"]),
        },
        "purchaseUrls": {
            "tcgplayer": TCGPLAYER_REFERRAL_URL.format(tcgplayer_token["productId"])
        },
    }


def map_uuids_back_to_single_uuid(
    filtered: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    The main system will populate an "uuids" field within the tokenParts. This
    needs to be broken down into individual UUIDs, for consistency, since each
    entry should only have one UUID to link back to in the MTGJSON data set.

    :param filtered: A "final" format of the token mapping
    :return: The same "final" format of token mapping, but with UUIDs mapped back to single UUIDs
    """
    tp = "tokenParts"
    for uuid, output_tokens in filtered.items():
        for output_index, output_token in enumerate(output_tokens):
            for token_part_index, token_part in enumerate(
                output_token.get("tokenParts", [])
            ):
                if "uuids" not in token_part:
                    continue
                if uuid in token_part["uuids"]:
                    filtered[uuid][output_index][tp][token_part_index]["uuid"] = uuid
                else:
                    filtered[uuid][output_index][tp][token_part_index]["uuid"] = (
                        token_part["uuids"][0]
                    )
                del filtered[uuid][output_index][tp][token_part_index]["uuids"]

    return filtered


def filter_tokens_without_uuids(
    output_tokens: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """
    If we don't have a UUID to map back to, we will drop this
    token from the data set.
    :param output_tokens: Tokens to check for UUIDs
    :return: A "final" format of the token mapping, where at least one UUID exists
    """
    output_dict_of_tokens = defaultdict(list)
    for output_token in output_tokens:
        for token_part in output_token["tokenParts"]:
            if "uuids" in token_part:
                # These entities are for internal use only
                token_part.pop("tokenType")
                token_part.pop("faceId")
                token_part.pop("faceName")
                for uuid in token_part["uuids"]:
                    output_dict_of_tokens[uuid].append(output_token)

    return output_dict_of_tokens


def add_backside_of_art_cards(
    filtered_tokens_uuid_mapping: Dict[str, List[Dict[str, Any]]],
    mtgjson_art_cards_front_to_back_mapping: Dict[str, str],
) -> Dict[str, List[Dict[str, Any]]]:
    new_output_tokens = defaultdict(list)

    for uuid, token_parts in filtered_tokens_uuid_mapping.items():
        if uuid in mtgjson_art_cards_front_to_back_mapping:
            back_side_uuid = mtgjson_art_cards_front_to_back_mapping[uuid]
            new_output_tokens[back_side_uuid].extend(token_parts)

        new_output_tokens[uuid].extend(token_parts)

    return new_output_tokens


def build_tokens_mapping(
    set_code,
    mtgjson_tokens: Dict[str, List[Dict[str, Any]]],
    tcgplayer_tokens: List[Dict[str, Any]],
    tcgplayer_token_parser: TcgplayerTokenParser,
) -> Dict[str, List[Dict[str, Any]]]:
    tokens = []
    mapper = MtgjsonToTcgplayerMapper()

    mtgjson_art_cards_front_to_back_mapping = (
        MtgjsonToTcgplayerMapper().art_card_front_to_back_mapping(mtgjson_tokens)
    )

    for tcgplayer_token in tcgplayer_tokens:
        tcgplayer_token_face_details = (
            tcgplayer_token_parser.split_tcgplayer_token_faces_details(tcgplayer_token)
        )
        mapper.add_mtgjson_uuids_to_tcgplayer_token_face_details(
            set_code, mtgjson_tokens, tcgplayer_token_face_details
        )

        tokens.append(
            {
                **tcgplayer_token_to_mtgjson_token_products_entry(tcgplayer_token),
                "tokenParts": tcgplayer_token_face_details,
            }
        )

    filtered = filter_tokens_without_uuids(tokens)
    filtered = map_uuids_back_to_single_uuid(filtered)
    filtered = add_backside_of_art_cards(
        filtered, mtgjson_art_cards_front_to_back_mapping
    )
    return filtered


def save_output(parent_set_code: str, output: Dict[str, List[Dict[str, Any]]]) -> None:
    output_dir = pathlib.Path("outputs/token_products_mappings")
    output_dir.mkdir(parents=True, exist_ok=True)
    with output_dir.joinpath(f"{parent_set_code}.json").open("w") as fp:
        json.dump(output, fp, indent=4, sort_keys=True)


def main():
    mtgjson_parser = MtgjsonParser()
    tcgplayer_provider = TcgplayerProvider()
    tcgplayer_token_parser = TcgplayerTokenParser()

    overrides = import_overrides()
    for set_code, group_ids in mtgjson_parser.get_codes_to_group_ids_mapping().items():
        print(f"Processing {set_code}")
        mtgjson_tokens = mtgjson_parser.get_associated_mtgjson_tokens(set_code)
        tcgplayer_tokens = tcgplayer_provider.get_tokens_from_group_ids(group_ids)

        output_token_mapping = build_tokens_mapping(
            set_code, mtgjson_tokens, tcgplayer_tokens, tcgplayer_token_parser
        )
        output_token_mapping.update(overrides.get(set_code, {}))

        if output_token_mapping:
            save_output(set_code, output_token_mapping)


if __name__ == "__main__":
    main()

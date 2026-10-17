from ..atomic_write import atomic_write

import json
from copy import deepcopy
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

    A face can match several MTGJSON tokens that share a name and number (for
    example a parent set token and its Commander reprint). On a multi-face
    product each face resolves to its first match, which the mapper orders so
    the set selling the product comes first, and every token listing the
    product agrees on which printings make it up. A single-face product, such
    as an art card, is listed under every token it matches and names that
    token as its face.

    :param filtered: A "final" format of the token mapping
    :return: The same "final" format of token mapping, but with UUIDs mapped back to single UUIDs
    """
    for uuid, output_tokens in filtered.items():
        for output_token in output_tokens:
            token_parts = output_token.get("tokenParts", [])
            for token_part in token_parts:
                if "uuids" not in token_part:
                    continue
                uuids = token_part.pop("uuids")
                if len(token_parts) == 1 and uuid in uuids:
                    token_part["uuid"] = uuid
                else:
                    token_part["uuid"] = uuids[0]

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
        # A multi-face product is listed only under the token each face
        # resolves to, and a UUID on both faces receives it once.
        token_parts = output_token["tokenParts"]
        if len(token_parts) == 1:
            uuids = dict.fromkeys(token_parts[0].get("uuids", []))
        else:
            uuids = dict.fromkeys(
                part["uuids"][0] for part in token_parts if part.get("uuids")
            )
        for uuid in uuids:
            entry = deepcopy(output_token)
            for part in entry["tokenParts"]:
                if "uuids" in part:
                    for key in ("tokenType", "faceId", "faceName", "setCodeHint"):
                        part.pop(key, None)
            # Conversion below mutates tokenParts for this specific UUID.
            output_dict_of_tokens[uuid].append(entry)

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
    set_code_to_group_id: Dict[str, int] | None = None,
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
            set_code,
            mtgjson_tokens,
            tcgplayer_token_face_details,
            tcgplayer_token.get("groupId"),
            set_code_to_group_id,
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
    with atomic_write(output_dir.joinpath(f'{parent_set_code}.json')) as fp:
        json.dump(output, fp, indent=4, sort_keys=True)


def main():
    print("Initializing MTGJSON parser...")
    mtgjson_parser = MtgjsonParser()
    print("Initializing TCGplayer provider...")
    tcgplayer_provider = TcgplayerProvider()
    tcgplayer_token_parser = TcgplayerTokenParser()

    overrides = import_overrides()
    set_code_mapping = mtgjson_parser.get_codes_to_group_ids_mapping()
    set_code_to_group_id = mtgjson_parser.get_code_to_own_group_id_mapping()
    total = len(set_code_mapping)
    print(f"Processing {total} sets...")

    for i, (set_code, group_ids) in enumerate(set_code_mapping.items(), 1):
        print(f"[{i}/{total}] Processing {set_code} (group IDs: {group_ids})")
        mtgjson_tokens = mtgjson_parser.get_associated_mtgjson_tokens(set_code)
        tcgplayer_tokens = tcgplayer_provider.get_tokens_from_group_ids(group_ids)

        output_token_mapping = build_tokens_mapping(
            set_code,
            mtgjson_tokens,
            tcgplayer_tokens,
            tcgplayer_token_parser,
            set_code_to_group_id,
        )
        output_token_mapping.update(overrides.get(set_code, {}))

        if output_token_mapping:
            save_output(set_code, output_token_mapping)
            print(f"  Saved {len(output_token_mapping)} token mapping(s)")
        else:
            print(f"  No token mappings found, skipping")

    print("Done!")


if __name__ == "__main__":
    main()

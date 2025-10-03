import json
from collections import defaultdict

import pathlib
from typing import Dict, List, Any

from scripts.tokens.mtgjson_parser import MtgjsonParser
from scripts.tokens.tcgplayer_provider import TcgplayerProvider
from scripts.tokens.tcgplayer_token_parser import TcgplayerTokenParser

TCGPLAYER_REFERRAL_URL: str = (
    "https://partner.tcgplayer.com/c/4948039/1780961/21018?subId1=api&u="
    "https%3A%2F%2Fwww.tcgplayer.com%2Fproduct%2F{}%3Fpage%3D1"
)


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


def add_mtgjson_uuids_to_tcgplayer_token_face_details(
    mtgjson_tokens: Dict[str, List[Dict[str, Any]]],
    tcgplayer_token_face_details: List[Dict[str, Any]],
) -> None:
    for tcgplayer_token_face_index, tcgplayer_token_face in enumerate(
        tcgplayer_token_face_details
    ):
        for mtgjson_token_key, mtgjson_token_data in mtgjson_tokens.items():
            for mtgjson_token_index, mtgjson_token in enumerate(mtgjson_token_data):
                if (mtgjson_token["name"] == tcgplayer_token_face["faceName"]) and (
                    mtgjson_token["number"] == tcgplayer_token_face["faceId"]
                ):
                    tcgplayer_token_face_details[tcgplayer_token_face_index]["uuid"] = (
                        mtgjson_token["uuid"]
                    )
                    break
                elif mtgjson_token.get("faceName") == tcgplayer_token_face["faceName"]:
                    # This is for Punchcard // Punchcard tokens to avoid duplication
                    mtgjson_tokens[mtgjson_token_key][mtgjson_token_index][
                        "faceName"
                    ] = ""
                    tcgplayer_token_face_details[tcgplayer_token_face_index]["uuid"] = (
                        mtgjson_token["uuid"]
                    )
                    break


def filter_tokens_without_uuids(
    output_tokens: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    output_dict_of_tokens = defaultdict(list)
    for output_token in output_tokens:
        for token_part in output_token["tokenParts"]:
            if "uuid" in token_part:
                output_dict_of_tokens[token_part["uuid"]].append(output_token)

    return output_dict_of_tokens


def build_tokens_mapping(
    mtgjson_tokens: Dict[str, List[Dict[str, Any]]],
    tcgplayer_tokens,
    tcgplayer_token_parser: TcgplayerTokenParser,
):
    output_tokens = []

    for tcgplayer_token in tcgplayer_tokens:
        tcgplayer_token_face_details = (
            tcgplayer_token_parser.split_tcgplayer_token_faces_details(tcgplayer_token)
        )
        add_mtgjson_uuids_to_tcgplayer_token_face_details(
            mtgjson_tokens, tcgplayer_token_face_details
        )

        output_tokens.append(
            {
                **tcgplayer_token_to_mtgjson_token_products_entry(tcgplayer_token),
                "tokenParts": tcgplayer_token_face_details,
            }
        )

    return filter_tokens_without_uuids(output_tokens)


def save_output(set_code: str, output: Dict[str, List[Dict[str, Any]]]) -> None:
    output_dir = pathlib.Path("outputs/token_products_mappings")
    output_dir.mkdir(parents=True, exist_ok=True)
    with output_dir.joinpath(f"{set_code}.json").open("w") as fp:
        json.dump(output, fp, indent=4, sort_keys=True)


def main():
    mtgjson_parser = MtgjsonParser()
    tcgplayer_provider = TcgplayerProvider()
    tcgplayer_token_parser = TcgplayerTokenParser()

    for set_code, group_ids in mtgjson_parser.get_iter().items():
        mtgjson_tokens = mtgjson_parser.get_associated_mtgjson_tokens(set_code)
        tcgplayer_tokens = tcgplayer_provider.get_tokens_from_group_ids(group_ids)

        output_token_mapping = build_tokens_mapping(
            mtgjson_tokens, tcgplayer_tokens, tcgplayer_token_parser
        )

        if output_token_mapping:
            save_output(set_code, output_token_mapping)


if __name__ == "__main__":
    main()

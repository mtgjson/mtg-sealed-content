import json
import re
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
    print(f"Looking for {tcgplayer_token_face_details}")

    for tcgplayer_token_face_index, tcgplayer_token_face in enumerate(
        tcgplayer_token_face_details
    ):
        found = False
        for mtgjson_token_key, mtgjson_token_data in mtgjson_tokens.items():
            for mtgjson_token_index, mtgjson_token in enumerate(mtgjson_token_data):
                # Handle Art Cards
                if tcgplayer_token_face["tokenType"] == "Art":
                    if mtgjson_token["layout"] == "art_series":
                        if (
                            f"{tcgplayer_token_face['faceName']} // {tcgplayer_token_face['faceName']}"
                            == mtgjson_token["name"]
                            and mtgjson_token["number"].rstrip("s")
                            == tcgplayer_token_face["faceId"]
                        ):
                            print(f"> Found Art Card for {tcgplayer_token_face}")
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ] = mtgjson_token["uuid"]
                            found = True
                            break
                # Handle theme headers
                elif tcgplayer_token_face["tokenType"] == "Theme":
                    if mtgjson_token["layout"] == "token":
                        if (
                            f"{tcgplayer_token_face['faceName']}"
                            == mtgjson_token["name"]
                            and mtgjson_token["number"]
                            == tcgplayer_token_face["faceId"]
                        ):
                            print(f"> Found Theme Card for {tcgplayer_token_face}")
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ] = mtgjson_token["uuid"]
                            found = True
                            break
                # Handle Tokens
                elif tcgplayer_token_face["tokenType"] == "Token":
                    if (mtgjson_token["name"] == tcgplayer_token_face["faceName"]) and (
                        mtgjson_token["number"] == tcgplayer_token_face["faceId"]
                    ):
                        print(f"> Found Token for {tcgplayer_token_face}")
                        tcgplayer_token_face_details[tcgplayer_token_face_index][
                            "uuid"
                        ] = mtgjson_token["uuid"]
                        found = True
                        break
                    elif (
                        mtgjson_token["layout"] == "double_faced_token"
                        and tcgplayer_token_face["faceName"] in mtgjson_token["faceName"]
                        and mtgjson_token["number"] == tcgplayer_token_face["faceId"]
                    ):
                        print(f"> Found DF Token for {tcgplayer_token_face}")
                        tcgplayer_token_face_details[tcgplayer_token_face_index][
                            "uuid"
                        ] = mtgjson_token["uuid"]
                        found = True
                        break
                elif tcgplayer_token_face["tokenType"] == "Bio":
                    # 1996 Bertrand Lestree Biography Card
                    if match := re.match(r"\d+ (.*) (.*) Biography", tcgplayer_token_face["faceName"]):
                        result = str(match.group(1)) + " " + str(match.group(2)) + " Bio"
                        if mtgjson_token["name"] == result:
                            print(f"> Found Bio for {tcgplayer_token_face}")
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ] = mtgjson_token["uuid"]
                            found = True
                            break
                elif tcgplayer_token_face["tokenType"] == "Decklist":
                    if match := re.match(r"\d+ (.*) (.*) Decklist", tcgplayer_token_face["faceName"]):
                        result = str(match.group(1)) + " " + str(match.group(2)) + " Decklist"
                        if mtgjson_token["name"] == result:
                            print(f"> Found Decklist for {tcgplayer_token_face}")
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ] = mtgjson_token["uuid"]
                            found = True
                            break


        if not found:
            pass
            print(f">> UNABLE to find UUID for {tcgplayer_token_face}")


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
        print(f"TCGPlayer Token: {tcgplayer_token}")
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
        # if set_code != "WC00":
        #     continue
        print(f"Processing {set_code}")
        mtgjson_tokens = mtgjson_parser.get_associated_mtgjson_tokens(set_code)
        tcgplayer_tokens = tcgplayer_provider.get_tokens_from_group_ids(group_ids)

        output_token_mapping = build_tokens_mapping(
            mtgjson_tokens, tcgplayer_tokens, tcgplayer_token_parser
        )

        if output_token_mapping:
            save_output(set_code, output_token_mapping)
        # break


if __name__ == "__main__":
    main()

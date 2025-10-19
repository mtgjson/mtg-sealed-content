import re
from typing import Dict, List, Any


class MtgjsonToTcgplayerMapper:
    bio_regex: re.Pattern
    decklist_regex: re.Pattern

    def __init__(self) -> None:
        self.bio_regex = re.compile(r"(\d+) (.*) Biography")
        self.decklist_regex = re.compile(r"(\d+) (.*) Decklist")

    def add_mtgjson_uuids_to_tcgplayer_token_face_details(
        self,
        mtgjson_tokens: Dict[str, List[Dict[str, Any]]],
        tcgplayer_token_face_details: List[Dict[str, Any]],
    ) -> None:
        print(f"Looking for {tcgplayer_token_face_details}")

        for tcgplayer_token_face_index, tcgplayer_token_face in enumerate(
            tcgplayer_token_face_details
        ):
            found = False
            for mtgjson_token_key, mtgjson_token_data in mtgjson_tokens.items():
                for mtgjson_token in mtgjson_token_data:
                    # Handle Art Cards
                    if tcgplayer_token_face["tokenType"] == "Art":
                        if mtgjson_token["layout"] != "art_series":
                            continue

                        if (
                            f"{tcgplayer_token_face['faceName']} // {tcgplayer_token_face['faceName']}"
                            == mtgjson_token["name"]
                            and mtgjson_token["number"].rstrip(
                                "s"
                            )  # Removing the "s" for "signed"
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
                        if mtgjson_token["layout"] != "token":
                            continue
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
                        if (
                            mtgjson_token["name"] == tcgplayer_token_face["faceName"]
                        ) and (
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
                            and tcgplayer_token_face["faceName"]
                            in mtgjson_token["faceName"]
                            and mtgjson_token["number"]
                            == tcgplayer_token_face["faceId"]
                        ):
                            print(f"> Found DF Token for {tcgplayer_token_face}")
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ] = mtgjson_token["uuid"]
                            found = True
                            break
                    elif tcgplayer_token_face["tokenType"] == "Bio":
                        if match := self.bio_regex.match(
                            tcgplayer_token_face["faceName"]
                        ):
                            result = (
                                str(match.group(1)) + " " + str(match.group(2)) + " Bio"
                            )
                            if mtgjson_token["name"] == result:
                                print(f"> Found Bio for {tcgplayer_token_face}")
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"] = mtgjson_token["uuid"]
                                found = True
                                break
                    elif tcgplayer_token_face["tokenType"] == "Decklist":
                        if match := self.decklist_regex.match(
                            tcgplayer_token_face["faceName"]
                        ):
                            result = (
                                str(match.group(1))
                                + " "
                                + str(match.group(2))
                                + " Decklist"
                            )
                            if mtgjson_token["name"] == result:
                                print(f"> Found Decklist for {tcgplayer_token_face}")
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"] = mtgjson_token["uuid"]
                                found = True
                                break

            if not found:
                pass
                print(f">> UNABLE to find UUID for {tcgplayer_token_face}")

    @staticmethod
    def mtgjson_art_card_front_to_back_mapping(mtgjson_tokens) -> Dict[str, str]:
        front_to_back_mapping = {}

        for mtgjson_token_key, mtgjson_token_data in mtgjson_tokens.items():
            for index, mtgjson_token in enumerate(mtgjson_token_data):
                if mtgjson_token["layout"] != "art_series":
                    continue

                if mtgjson_token["side"] != "a":
                    continue

                front_to_back_mapping[mtgjson_token["uuid"]] = mtgjson_token_data[
                    index + 1
                ]["uuid"]

        return front_to_back_mapping

    def add_art_cards_back_mapping(self, mtgjson_tokens, tcgplayer_token_face_details):
        pass

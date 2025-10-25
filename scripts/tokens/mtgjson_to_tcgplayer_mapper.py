import re
import unidecode
from typing import Dict, List, Any


class MtgjsonToTcgplayerMapper:
    bio_regex: re.Pattern
    decklist_regex: re.Pattern

    def __init__(self) -> None:
        self.bio_regex = re.compile(r"(\d+) (.*) Biography")
        self.decklist_regex = re.compile(r"(\d+) (.*) Decklist")

    @staticmethod
    def strip_star(number: str | None) -> str | None:
        if number:
            return number.replace("*", "").replace("★", "")
        return ""

    def compare_face_name_and_number(
        self, tcgplayer_face_name, tcgplayer_face_id, mtgjson_name, mtgjson_number
    ):
        return (
            unidecode.unidecode(tcgplayer_face_name)
            == unidecode.unidecode(mtgjson_name)
        ) and (self.strip_star(mtgjson_number).rstrip("s") == tcgplayer_face_id)

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
            for mtgjson_token_data in mtgjson_tokens.values():
                for mtgjson_token in mtgjson_token_data:
                    # Handle Art Cards
                    if tcgplayer_token_face["tokenType"] == "Art":
                        if mtgjson_token["layout"] != "art_series":
                            continue

                        if self.compare_face_name_and_number(
                            f"{tcgplayer_token_face['faceName']} // {tcgplayer_token_face['faceName']}",
                            tcgplayer_token_face["faceId"],
                            mtgjson_token["name"],
                            mtgjson_token["number"],
                        ):
                            print(f"> Found Art Card for {tcgplayer_token_face}")
                            if (
                                "uuid"
                                not in tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]
                            ):
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"] = []
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ].append(mtgjson_token["uuid"])
                            found = True
                            # break

                        if unidecode.unidecode(
                            f"{tcgplayer_token_face['faceName']} //"
                        ) in unidecode.unidecode(
                            mtgjson_token["name"]
                        ) or unidecode.unidecode(
                            f"// {tcgplayer_token_face['faceName']}"
                        ) in unidecode.unidecode(
                            mtgjson_token["name"]
                        ):
                            print(f"> Found Art Card for {tcgplayer_token_face}")
                            if (
                                "uuid"
                                not in tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]
                            ):
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"] = []
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ].append(mtgjson_token["uuid"])
                            found = True

                    # Handle theme headers
                    elif tcgplayer_token_face["tokenType"] == "Theme":
                        if mtgjson_token["layout"] != "token":
                            continue

                        if self.compare_face_name_and_number(
                            tcgplayer_token_face["faceName"],
                            tcgplayer_token_face["faceId"],
                            mtgjson_token["name"],
                            mtgjson_token["number"],
                        ):
                            print(f"> Found Theme Card for {tcgplayer_token_face}")
                            if (
                                "uuid"
                                not in tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]
                            ):
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"] = []
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ].append(mtgjson_token["uuid"])
                            found = True
                            # break
                    # Handle Tokens
                    elif tcgplayer_token_face["tokenType"] == "Token":
                        if self.compare_face_name_and_number(
                            tcgplayer_token_face["faceName"],
                            tcgplayer_token_face["faceId"],
                            mtgjson_token["name"],
                            mtgjson_token["number"],
                        ):
                            print(f"> Found Token for {tcgplayer_token_face}")
                            if (
                                "uuid"
                                not in tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]
                            ):
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"] = []
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ].append(mtgjson_token["uuid"])
                            found = True
                            # break
                        elif (
                            mtgjson_token["layout"] == "double_faced_token"
                        ) and self.compare_face_name_and_number(
                            tcgplayer_token_face["faceName"],
                            tcgplayer_token_face["faceId"],
                            mtgjson_token["name"],
                            mtgjson_token["number"],
                        ):
                            print(f"> Found DF Token for {tcgplayer_token_face}")
                            if (
                                "uuid"
                                not in tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]
                            ):
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"] = []
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ].append(mtgjson_token["uuid"])
                            found = True
                        elif (tcgplayer_token_face["faceName"] == "Punchcard") and (
                            mtgjson_token["name"] == "Punchcard // Punchcard"
                        ):
                            print(f"> Found Punch Token for {tcgplayer_token_face}")
                            if (
                                "uuid"
                                not in tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]
                            ):
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"] = []
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ].append(mtgjson_token["uuid"])
                            found = True
                        elif tcgplayer_token_face["faceName"] == "Helper Card" and tcgplayer_token_face["faceId"] == mtgjson_token["number"] and mtgjson_token["type"] == "Card" and "Substitute" in mtgjson_token["name"]:
                            print(f"> Found Helper Token for {tcgplayer_token_face}")
                            if (
                                    "uuid"
                                    not in tcgplayer_token_face_details[
                                tcgplayer_token_face_index
                            ]
                            ):
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"] = []
                            tcgplayer_token_face_details[tcgplayer_token_face_index][
                                "uuid"
                            ].append(mtgjson_token["uuid"])
                            found = True
                    elif tcgplayer_token_face["tokenType"] == "Bio":
                        if match := self.bio_regex.match(
                            tcgplayer_token_face["faceName"]
                        ):
                            result = str(match.group(2)) + " Bio"
                            year = match.group(1)
                            if (
                                unidecode.unidecode(mtgjson_token["name"]) == result
                                or unidecode.unidecode(mtgjson_token["name"])
                                == result + f" ({year})"
                            ):
                                print(f"> Found Bio for {tcgplayer_token_face}")
                                if (
                                    "uuid"
                                    not in tcgplayer_token_face_details[
                                        tcgplayer_token_face_index
                                    ]
                                ):
                                    tcgplayer_token_face_details[
                                        tcgplayer_token_face_index
                                    ]["uuid"] = []
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"].append(mtgjson_token["uuid"])
                                found = True
                                # break
                    elif tcgplayer_token_face["tokenType"] == "Decklist":
                        if match := self.decklist_regex.match(
                            tcgplayer_token_face["faceName"]
                        ):
                            result = str(match.group(2)) + " Decklist"
                            year = str(match.group(1))
                            # print(f">>>Checking {result} against {unidecode.unidecode(mtgjson_token['name'])}")
                            if (
                                unidecode.unidecode(mtgjson_token["name"]) == result
                                or unidecode.unidecode(mtgjson_token["name"])
                                == result + f" ({year})"
                            ):
                                print(f"> Found Decklist for {tcgplayer_token_face}")
                                if (
                                    "uuid"
                                    not in tcgplayer_token_face_details[
                                        tcgplayer_token_face_index
                                    ]
                                ):
                                    tcgplayer_token_face_details[
                                        tcgplayer_token_face_index
                                    ]["uuid"] = []
                                tcgplayer_token_face_details[
                                    tcgplayer_token_face_index
                                ]["uuid"].append(mtgjson_token["uuid"])
                                found = True
                                # break

            if not found:
                pass
                print(f">> UNABLE to find UUID for {tcgplayer_token_face}")

    @staticmethod
    def mtgjson_art_card_front_to_back_mapping(mtgjson_tokens) -> Dict[str, str]:
        front_to_back_mapping = {}

        for mtgjson_token_data in mtgjson_tokens.values():
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

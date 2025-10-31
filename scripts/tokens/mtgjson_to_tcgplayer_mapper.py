import re
from collections.abc import Callable

import unidecode
from typing import Dict, List, Any


class MtgjsonToTcgplayerMapper:
    bio_regex: re.Pattern
    decklist_regex: re.Pattern

    def __init__(self) -> None:
        self.bio_regex = re.compile(r"(\d+) (.*) Biography")
        self.decklist_regex = re.compile(r"(\d+) (.*) Decklist")
        self.wc_blank_regex = re.compile(r"(\d+) World Championship Blank Card")

    @staticmethod
    def strip_star(number: str | None) -> str | None:
        if number:
            return number.replace("*", "").replace("★", "")
        return ""

    @staticmethod
    def strip_quotes(mtgjson_token_name: str) -> str:
        return mtgjson_token_name.replace('"', "")

    def compare_face_name_and_number(
        self, tcgplayer_face_name, tcgplayer_face_id, mtgjson_name, mtgjson_number
    ):
        name_match = unidecode.unidecode(tcgplayer_face_name) == unidecode.unidecode(
            self.strip_quotes(mtgjson_name)
        )

        mtgjson_clean_num = self.strip_star(mtgjson_number)
        if not mtgjson_clean_num:
            return False

        number_match = self.compare_numbers_safely(mtgjson_clean_num, tcgplayer_face_id)

        return name_match and number_match

    @staticmethod
    def add_uuid_to_list(
        tcgplayer_token_face_details, tcgplayer_token_face_index, mtgjson_token
    ):
        if "uuids" not in tcgplayer_token_face_details[tcgplayer_token_face_index]:
            tcgplayer_token_face_details[tcgplayer_token_face_index]["uuids"] = []
        tcgplayer_token_face_details[tcgplayer_token_face_index]["uuids"].append(
            mtgjson_token["uuid"]
        )

    @staticmethod
    def compare_numbers_safely(mtgjson_num: str, tcgplayer_id: str) -> bool:
        if not mtgjson_num:
            return False

        if mtgjson_num == tcgplayer_id:
            return True

        if mtgjson_num.endswith("s") and mtgjson_num.rstrip("s") == tcgplayer_id:
            return True

        return False

    def match_art_card(self, mtgjson_token, tcgplayer_token_face):
        if mtgjson_token["layout"] != "art_series":
            return False

        if self.compare_face_name_and_number(
            f"{tcgplayer_token_face['faceName']} // {tcgplayer_token_face['faceName']}",
            tcgplayer_token_face["faceId"],
            mtgjson_token["name"],
            mtgjson_token["number"],
        ):
            return True

        if unidecode.unidecode(
            f"{tcgplayer_token_face['faceName']} //"
        ) in unidecode.unidecode(
            self.strip_quotes(mtgjson_token["name"])
        ) or unidecode.unidecode(
            f"// {tcgplayer_token_face['faceName']}"
        ) in unidecode.unidecode(
            self.strip_quotes(mtgjson_token["name"])
        ):
            return True

        return False

    def match_theme_card(self, mtgjson_token, tcgplayer_token_face):
        if mtgjson_token["layout"] != "token":
            return False
        return self.compare_face_name_and_number(
            tcgplayer_token_face["faceName"],
            tcgplayer_token_face["faceId"],
            mtgjson_token["name"],
            mtgjson_token["number"],
        )

    def match_bio_card(self, mtgjson_token, tcgplayer_token_face):
        if match := self.bio_regex.match(tcgplayer_token_face["faceName"]):
            result = unidecode.unidecode(str(match.group(2)) + " Bio")
            year = match.group(1)
            if (
                unidecode.unidecode(mtgjson_token["name"]) == result
                or unidecode.unidecode(mtgjson_token["name"]) == result + f" ({year})"
                or unidecode.unidecode(mtgjson_token["name"]) == result + f" {year}"
            ):
                return True

        return False

    def match_decklist_card(self, mtgjson_token, tcgplayer_token_face):
        if match := self.decklist_regex.match(tcgplayer_token_face["faceName"]):
            result = str(match.group(2)) + " Decklist"
            year = str(match.group(1))
            if (
                unidecode.unidecode(mtgjson_token["name"]) == result
                or unidecode.unidecode(mtgjson_token["name"]) == result + f" ({year})"
                or unidecode.unidecode(mtgjson_token["name"]) == result + f" {year}"
            ):
                return True
        return False

    def handle_art_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if not self.match_art_card(mtgjson_token, tcgplayer_token_face):
            return False
        print(f"> Found Art Card for {tcgplayer_token_face}")
        self.add_uuid_to_list(
            tcgplayer_token_face_details,
            tcgplayer_token_face_index,
            mtgjson_token,
        )
        return True

    def handle_theme_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if not self.match_theme_card(mtgjson_token, tcgplayer_token_face):
            return False
        print(f"> Found Theme Card for {tcgplayer_token_face}")

        self.add_uuid_to_list(
            tcgplayer_token_face_details,
            tcgplayer_token_face_index,
            mtgjson_token,
        )
        return True

    def handle_tokens(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):

        mtgjson_token_number = mtgjson_token["number"].split("-")[-1]
        if mtgjson_token_number[0].isalpha() and set_code in {"MED"}:
            mtgjson_token_number = str(mtgjson_token_number[1:])

        if self.compare_face_name_and_number(
            tcgplayer_token_face["faceName"],
            tcgplayer_token_face["faceId"],
            (
                mtgjson_token.get("faceName", mtgjson_token.get("name"))
                if set_code in {"UST"}
                else mtgjson_token["name"]
            ),
            mtgjson_token_number,
        ):
            print(f"> Found Token for {tcgplayer_token_face}")

            self.add_uuid_to_list(
                tcgplayer_token_face_details,
                tcgplayer_token_face_index,
                mtgjson_token,
            )
            return True

        if (
            mtgjson_token["layout"] == "double_faced_token"
        ) and self.compare_face_name_and_number(
            tcgplayer_token_face["faceName"],
            tcgplayer_token_face["faceId"],
            mtgjson_token["name"],
            mtgjson_token["number"],
        ):
            print(f"> Found DF Token for {tcgplayer_token_face}")
            self.add_uuid_to_list(
                tcgplayer_token_face_details,
                tcgplayer_token_face_index,
                mtgjson_token,
            )
            return True

        # OTJ Bounty Cards are weird
        if mtgjson_token["layout"] == "double_faced_token" and mtgjson_token[
            "name"
        ].startswith("Bounty:"):
            if tcgplayer_token_face["faceId"] == mtgjson_token["number"]:
                print(f"> Found Bounty Token for {tcgplayer_token_face}")
                self.add_uuid_to_list(
                    tcgplayer_token_face_details,
                    tcgplayer_token_face_index,
                    mtgjson_token,
                )
                return True

        return False

    def handle_punch_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if (tcgplayer_token_face["faceName"] == "Punchcard") and (
            mtgjson_token["name"] == "Punchcard // Punchcard"
        ):
            print(f"> Found Punch Token for {tcgplayer_token_face}")
            self.add_uuid_to_list(
                tcgplayer_token_face_details,
                tcgplayer_token_face_index,
                mtgjson_token,
            )
            return True

        return False

    def handle_helper_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if (
            tcgplayer_token_face["faceName"] == "Helper Card"
            and tcgplayer_token_face["faceId"] == mtgjson_token["number"]
            and mtgjson_token["type"] == "Card"
            and "Substitute" in mtgjson_token["name"]
        ):
            print(f"> Found Helper Token for {tcgplayer_token_face}")
            self.add_uuid_to_list(
                tcgplayer_token_face_details,
                tcgplayer_token_face_index,
                mtgjson_token,
            )
            return True

        return False

    def handle_decklist_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if not self.match_decklist_card(mtgjson_token, tcgplayer_token_face):
            return False
        print(f"> Found Decklist for {tcgplayer_token_face}")
        self.add_uuid_to_list(
            tcgplayer_token_face_details,
            tcgplayer_token_face_index,
            mtgjson_token,
        )
        return True

    def handle_minigame_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        # print(f">>>> {tcgplayer_token_face['faceName']} vs {mtgjson_token.get('faceName', '')}")
        # print(f">>>> {tcgplayer_token_face['faceId']} vs {mtgjson_token.get('number', '')}")

        if tcgplayer_token_face["faceName"].strip() == "Find The Assassin":
            if mtgjson_token.get("faceName", "").lower() == "find the assassin":
                pass

        if self.compare_face_name_and_number(
            tcgplayer_token_face["faceName"].lower(),
            tcgplayer_token_face["faceId"],
            mtgjson_token.get("faceName", "").lower(),
            mtgjson_token["number"],
        ):
            print(f"> Found Minigame for {tcgplayer_token_face}")

            self.add_uuid_to_list(
                tcgplayer_token_face_details,
                tcgplayer_token_face_index,
                mtgjson_token,
            )
            return True

        return False

    def handle_bio_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if not self.match_bio_card(mtgjson_token, tcgplayer_token_face):
            return False

        print(f"> Found Bio for {tcgplayer_token_face}")
        self.add_uuid_to_list(
            tcgplayer_token_face_details,
            tcgplayer_token_face_index,
            mtgjson_token,
        )
        return True

    def add_mtgjson_uuids_to_tcgplayer_token_face_details(
        self,
        set_code,
        mtgjson_tokens: Dict[str, List[Dict[str, Any]]],
        tcgplayer_token_face_details: List[Dict[str, Any]],
    ) -> None:
        print(f"Looking for {tcgplayer_token_face_details}")

        function_mapping: Dict[str, Callable[[Any, Any, Any, Any, Any], bool]] = {
            "Art": self.handle_art_cards,
            "Theme": self.handle_theme_cards,
            "Token": self.handle_tokens,
            "Punch": self.handle_punch_cards,
            "Helper": self.handle_helper_cards,
            "Bio": self.handle_bio_cards,
            "Decklist": self.handle_decklist_cards,
            "Minigame": self.handle_minigame_cards,
        }

        for tcgplayer_token_face_index, tcgplayer_token_face in enumerate(
            tcgplayer_token_face_details
        ):
            found = False
            for mtgjson_token_data in mtgjson_tokens.values():
                for mtgjson_token in mtgjson_token_data:
                    if tcgplayer_token_face["tokenType"] in function_mapping:
                        new_found = function_mapping[tcgplayer_token_face["tokenType"]](
                            set_code,
                            mtgjson_token,
                            tcgplayer_token_face_details,
                            tcgplayer_token_face_index,
                            tcgplayer_token_face,
                        )
                        found = found or new_found

            if not found:
                print(f">> UNABLE to find UUID for {tcgplayer_token_face}")

    @staticmethod
    def art_card_front_to_back_mapping(mtgjson_tokens) -> Dict[str, str]:
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

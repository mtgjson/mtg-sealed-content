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

    @staticmethod
    def rules_text_key(rules_text: str | None) -> str:
        # TCGplayer's rules text is HTML with reminder text in italics, and
        # MTGJSON puts reminder text in parentheses and symbols in braces.
        # Only the words are compared.
        rules_text = re.sub(r"<em>.*?</em>|\([^)]*\)", " ", rules_text or "")
        rules_text = re.sub(r"<[^>]+>|[{}]", " ", rules_text)
        return " ".join(re.findall(r"[\w+/'-]+", unidecode.unidecode(rules_text).casefold()))

    def compare_names(self, tcgplayer_face_name, mtgjson_name) -> bool:
        # TCGplayer and MTGJSON can differ in capitalization ("Primo, The
        # Indivisible") and MTGJSON sometimes keeps "Token" in the name.
        return unidecode.unidecode(tcgplayer_face_name).casefold() == unidecode.unidecode(
            self.strip_quotes(mtgjson_name)
        ).casefold().removesuffix(" token")

    def compare_face_name_and_number(
        self, tcgplayer_face_name, tcgplayer_face_id, mtgjson_name, mtgjson_number
    ):
        name_match = self.compare_names(tcgplayer_face_name, mtgjson_name)

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

        # TCGplayer can shorten an art card's name ("Death Tyrant" for
        # "Ghastly Death Tyrant"), so the face can end the front's name or
        # start the back's, as long as it does so on a word boundary.
        # Otherwise "Swamp" would match "Swampbenders".
        face_name = re.escape(unidecode.unidecode(tcgplayer_token_face["faceName"]))
        mtgjson_name = unidecode.unidecode(self.strip_quotes(mtgjson_token["name"]))
        return bool(
            re.search(rf"(?<!\w){face_name} //", mtgjson_name)
            or re.search(rf"// {face_name}(?!\w)", mtgjson_name)
        )

    def match_theme_card(self, mtgjson_token, tcgplayer_token_face):
        # MTGJSON carries newer theme cards as Jumpstart front cards.
        if mtgjson_token["layout"] not in {"token", "front_card"}:
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
        ) and any(
            self.compare_face_name_and_number(
                tcgplayer_token_face["faceName"],
                tcgplayer_token_face["faceId"],
                mtgjson_name,
                mtgjson_token["number"],
            )
            # A TCGplayer face can be the whole token or one side of it.
            for mtgjson_name in (mtgjson_token["name"], mtgjson_token.get("faceName"))
            if mtgjson_name
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
            tcgplayer_token_face["faceName"],
            tcgplayer_token_face["faceId"],
            mtgjson_token.get("faceName", ""),
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
        product_group_id: int | None = None,
        set_code_to_group_id: Dict[str, int] | None = None,
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

        star_uuids = {
            mtgjson_token["uuid"]
            for mtgjson_token_data in mtgjson_tokens.values()
            for mtgjson_token in mtgjson_token_data
            if mtgjson_token.get("number")
            and mtgjson_token["number"] != self.strip_star(mtgjson_token["number"])
        }
        uuid_to_set_code = {
            mtgjson_token["uuid"]: token_set_code
            for token_set_code, mtgjson_token_data in mtgjson_tokens.items()
            for mtgjson_token in mtgjson_token_data
        }
        uuid_to_power_toughness = {
            mtgjson_token["uuid"]: [
                str(mtgjson_token.get("power")),
                str(mtgjson_token.get("toughness")),
            ]
            for mtgjson_token_data in mtgjson_tokens.values()
            for mtgjson_token in mtgjson_token_data
        }
        uuid_to_rules_text = {
            mtgjson_token["uuid"]: self.rules_text_key(mtgjson_token.get("text"))
            for mtgjson_token_data in mtgjson_tokens.values()
            for mtgjson_token in mtgjson_token_data
        }

        def find(tcgplayer_token_face_index, tcgplayer_token_face) -> bool:
            found = False
            for mtgjson_token_data in mtgjson_tokens.values():
                for mtgjson_token in mtgjson_token_data:
                    if tcgplayer_token_face.get("tokenType") in function_mapping:
                        new_found = function_mapping[tcgplayer_token_face["tokenType"]](
                            set_code,
                            mtgjson_token,
                            tcgplayer_token_face_details,
                            tcgplayer_token_face_index,
                            tcgplayer_token_face,
                        )
                        found = found or new_found
            if found or len(tcgplayer_token_face_details) != 2:
                return found
            return self.match_unnumbered_face(
                mtgjson_tokens,
                tcgplayer_token_face,
                product_group_id,
                set_code_to_group_id or {},
            )

        found_faces = [
            find(index, face) for index, face in enumerate(tcgplayer_token_face_details)
        ]
        # TCGplayer sometimes lists a product's numbers in the opposite order
        # to its face names, as in "Treasure (0018) // Map" numbered "17 // 18".
        # The swap stands only if it matches both faces.
        if (
            len(found_faces) == 2
            and not any(found_faces)
            and tcgplayer_token_face_details[0]["faceId"]
            != tcgplayer_token_face_details[1]["faceId"]
        ):
            first, second = tcgplayer_token_face_details
            first["faceId"], second["faceId"] = second["faceId"], first["faceId"]
            found_faces = [
                find(index, face) for index, face in enumerate(tcgplayer_token_face_details)
            ]
            if not all(found_faces):
                first["faceId"], second["faceId"] = second["faceId"], first["faceId"]
                for face in tcgplayer_token_face_details:
                    face.pop("uuids", None)
                found_faces = [False, False]

        for tcgplayer_token_face, found in zip(tcgplayer_token_face_details, found_faces):
            if not found:
                print(f">> UNABLE to find UUID for {tcgplayer_token_face}")
                continue
            if tcgplayer_token_face.get("tokenType") == "Token":
                self.order_star_printings(tcgplayer_token_face, star_uuids)
            self.order_by_printing(
                tcgplayer_token_face,
                uuid_to_set_code,
                uuid_to_power_toughness,
                uuid_to_rules_text,
                product_group_id,
                set_code_to_group_id or {},
            )

    def match_unnumbered_face(
        self, mtgjson_tokens, tcgplayer_token_face, product_group_id, set_code_to_group_id
    ) -> bool:
        # A face of a double-sided product TCGplayer gives no number to, as
        # in Unfinity, can still match the one token with its name in the set
        # that sells the product. A single token without a number, like those
        # in the Asian promo tokens group, could be any set's.
        if (
            product_group_id is None
            or tcgplayer_token_face["faceId"]
            or tcgplayer_token_face.get("tokenType") != "Token"
        ):
            return False
        matches = [
            mtgjson_token
            for token_set_code, mtgjson_token_data in mtgjson_tokens.items()
            if set_code_to_group_id.get(token_set_code) == product_group_id
            for mtgjson_token in mtgjson_token_data
            if self.compare_names(tcgplayer_token_face["faceName"], mtgjson_token["name"])
        ]
        if len(matches) != 1:
            return False
        tcgplayer_token_face["uuids"] = [matches[0]["uuid"]]
        return True

    def order_by_printing(
        self,
        tcgplayer_token_face,
        uuid_to_set_code,
        uuid_to_power_toughness,
        uuid_to_rules_text,
        product_group_id,
        set_code_to_group_id,
    ) -> None:
        # A parent set and its Commander set can each print a token with the
        # same name and number, and a Commander product can carry either one.
        # The face belongs to the set TCGplayer names on the face itself, then
        # to the printing whose power and toughness TCGplayer lists for the
        # face, then to the printing with the face's rules text (The List's
        # Soldier #2 is GRN's with lifelink or CMR's without), then to the set
        # that sells the product. Applied after the star ordering, so this
        # decides first and stars break ties.
        set_code_hint = tcgplayer_token_face.get("setCodeHint")
        power_toughness_hint = tcgplayer_token_face.get("powerToughnessHint")
        rules_text_hint = self.rules_text_key(tcgplayer_token_face.get("rulesTextHint"))

        def rank(uuid):
            token_set_code = uuid_to_set_code.get(uuid)
            return (
                set_code_hint is not None and token_set_code != set_code_hint,
                power_toughness_hint is not None
                and uuid_to_power_toughness.get(uuid) != power_toughness_hint,
                bool(rules_text_hint) and uuid_to_rules_text.get(uuid) != rules_text_hint,
                product_group_id is not None
                and set_code_to_group_id.get(token_set_code) != product_group_id,
            )

        tcgplayer_token_face["uuids"].sort(key=rank)

    def order_star_printings(self, tcgplayer_token_face, star_uuids) -> None:
        # A ★ printing shares its number with the plain printing once the
        # star is stripped. A face sold as foil belongs to the ★ printing and
        # any other face to the plain one. The sort is stable, so matches of
        # the same kind keep the order they were found in.
        prefer_star = self.is_foil_face(tcgplayer_token_face)
        tcgplayer_token_face["uuids"].sort(
            key=lambda uuid: (uuid in star_uuids) != prefer_star
        )

    @staticmethod
    def is_foil_face(tcgplayer_token_face) -> bool:
        return any(
            "Foil" in attribute
            for attribute in tcgplayer_token_face.get("faceAttribute", [])
        )

    @staticmethod
    def art_card_front_to_back_mapping(mtgjson_tokens) -> Dict[str, str]:
        front_to_back_mapping = {}

        for mtgjson_token_data in mtgjson_tokens.values():
            for index, mtgjson_token in enumerate(mtgjson_token_data):
                if mtgjson_token["layout"] != "art_series":
                    continue

                if mtgjson_token["side"] != "a":
                    continue

                try:
                    front_to_back_mapping[mtgjson_token["uuid"]] = mtgjson_token_data[
                        index + 1
                    ]["uuid"]
                except IndexError:
                    print("Unable to get backside for " + mtgjson_token["name"] + " : " + mtgjson_token["uuid"])

        return front_to_back_mapping

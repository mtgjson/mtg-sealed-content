from typing import List, Any, Dict
import re


class TcgplayerTokenParser:
    __emblem_regex: re.Pattern
    __double_sided_token_regex: re.Pattern
    __treatment_single_side_regex: re.Pattern
    __treatment_double_side_regex: re.Pattern
    __role_regex: re.Pattern

    def __init__(self) -> None:
        """
        These regular expressions capture the essence of what TCGplayer tokens look like,
        in one form or another.

        Regexes supported:
        emblem: TCGPlayer emblems are "Emblem - <name>" whereas MTGJSON is "<name> Emblem".
        double_sided_token: TCGPlayer tokens are a bit wild and have inconsistent spacing/capitalization/spelling.
        treatment_single_side: TCGPlayer tokens are a bit wild and have inconsistent spacing/capitalization/spelling.
        role: Some TCGPlayer tokens are four tokens in one (Role1 Role // Role2 Role // Role3 Role // Role4 Role)
        """
        self.__emblem_regex = re.compile(r"Emblem - (.*)")
        self.__double_sided_token_regex = re.compile(r"^(.*) [Dd]oubled?[- ][Ss]ided")
        self.__treatment_single_side_regex = re.compile(
            r".*?(?:\((.*)\))? // .*?(?:\((.*)\))? [Dd]oubled?[- ][Ss]ided"
        )
        self.__treatment_double_side_regex = re.compile(
            r".*[Dd]oubled?[- ][Ss]ided Token \((.*?)\)"
        )
        self.__role_regex = re.compile(r"(.*) Role / (.*) Role")
        self.__face_set_code_regex = re.compile(r"\(\d+\S* ([A-Z][A-Z0-9]{1,4})\)")
        self.__face_number_regex = re.compile(r"\((\d+)\)")
        self.__face_separator_regex = re.compile(r"<br> ?// ?<br>")
        self.__face_header_regex = re.compile(r"<strong> ?(.*?) ?</strong>")

    def __fix_emblem_names(self, token) -> str:
        if match := self.__emblem_regex.match(token):
            return match.group(1) + " Emblem"
        return token

    def __get_token_face_names(self, token_name: str) -> List[str]:
        if token_name.lower().startswith(("punch card", "punchcard")):
            return ["Punchcard", "Punchcard"]
        if "helper card" in token_name.lower():
            return ["Helper Card"]

        if " // " in token_name:
            # Split cards are broken down into a left half and right half
            if match := self.__double_sided_token_regex.match(token_name):
                left, right = [
                    part.split(" (")[0].strip().removesuffix(" Token")
                    for part in match.group(1).split(" // ")
                ]

                if match := self.__role_regex.match(left):
                    left = f"{match.group(1)} // {match.group(2)}"
                if match := self.__role_regex.match(right):
                    right = f"{match.group(1)} // {match.group(2)}"

                return [
                    self.__fix_emblem_names(left),
                    self.__fix_emblem_names(right),
                ]

        # It's possible there's still a "(" in cards. We address this here
        if "(Art Series)" in token_name:
            return [token_name.split(" (Art Series)")[0]]
        if "(" in token_name:
            token_name = token_name.split(" (", 1)[0]
        if "Art Card" in token_name:
            return [token_name.split(" Art Card")[0]]
        if "Theme Card" in token_name:
            return [token_name.split(" Theme Card")[0]]
        if "Magic Minigame" in token_name:
            return [token_name.split("Magic Minigame: ")[-1]]

        token_name = token_name.split(" Token")[0]
        if match := self.__role_regex.match(token_name):
            return [f"{match.group(1)} // {match.group(2)}"]
        return [self.__fix_emblem_names(token_name)]

    def __get_face_numbers_from_name(self, token_name: str) -> List[str | None]:
        """
        Some TCGplayer products carry no number and name it on the face
        instead, as in "Clown Robot (002) // Food (010) Double-sided Token".
        """
        if match := self.__double_sided_token_regex.match(token_name):
            faces = match.group(1).split(" // ")
            if len(faces) == 2:
                return [
                    number.group(1).lstrip("0")
                    if (number := self.__face_number_regex.search(face))
                    else None
                    for face in faces
                ]
        return [None, None]

    def __get_face_set_code_hints(self, token_name: str) -> List[str | None]:
        """
        TCGplayer names the set of a face when a product pairs two tokens that
        share a name and number, as in "Zombie (005 MIC) // Zombie (005 MID)".
        """
        if match := self.__double_sided_token_regex.match(token_name):
            faces = match.group(1).split(" // ")
            if len(faces) == 2:
                return [
                    hint.group(1) if (hint := self.__face_set_code_regex.search(face)) else None
                    for face in faces
                ]
        return [None, None]

    @staticmethod
    def __get_face_power_toughness(tcgplayer_token: Dict[str, Any]) -> List[List[str] | None]:
        """
        TCGplayer lists a double-sided token's power and toughness per face, as
        P "4/1" and T "4/1" for a 4/4 front and a 1/1 back.
        """
        values = {
            raw_extended_data["name"]: raw_extended_data["value"].split("/")
            for raw_extended_data in tcgplayer_token["extendedData"]
            if raw_extended_data["name"] in ("P", "T")
        }
        powers, toughnesses = values.get("P", []), values.get("T", [])
        if len(powers) != 2 or len(toughnesses) != 2:
            return [None, None]
        return [
            [power.strip(), toughness.strip()]
            for power, toughness in zip(powers, toughnesses)
        ]

    def __get_face_rules_texts(
        self, tcgplayer_token: Dict[str, Any], face_names: List[str]
    ) -> List[str | None]:
        """
        TCGplayer gives a double-sided token's rules text in one field, with
        "//" between the faces or a face's name in bold before its text, as in
        "Lifelink<br>//<br><strong>Soldier</strong><br>Lifelink". Text that
        neither places on a face, such as a lone "Flying", is left out.
        """
        oracle_text = next(
            (
                raw_extended_data["value"]
                for raw_extended_data in tcgplayer_token["extendedData"]
                if raw_extended_data["name"] == "OracleText"
            ),
            "",
        )
        oracle_text = re.sub(r"\s+", " ", oracle_text)
        names = [name.casefold() for name in face_names]
        if not oracle_text or names[0] == names[1]:
            return [None, None]

        sides = self.__face_separator_regex.split(oracle_text)
        if len(sides) == 2:
            texts = []
            for name, side in zip(names, sides):
                side = side.strip()
                header = self.__face_header_regex.match(side)
                if header and header.group(1).casefold() == name:
                    side = side[header.end():]
                texts.append(side)
            return texts

        headers = [
            header
            for header in self.__face_header_regex.finditer(oracle_text)
            if header.group(1).casefold() in names
        ]
        texts = [None, None]
        for header, next_header in zip(headers, headers[1:] + [None]):
            end = next_header.start() if next_header else len(oracle_text)
            texts[names.index(header.group(1).casefold())] = oracle_text[header.end():end]
        # Text before the back's name is the front's.
        if headers and names.index(headers[0].group(1).casefold()) == 1:
            texts[0] = oracle_text[: headers[0].start()]
        return texts

    @staticmethod
    def get_additional_dict(
        tcgplayer_token_name_lower: str,
    ) -> Dict[str, str | list[str]]:
        """
        Determines the 'tokenType' and potential 'faceAttributes' based on keywords
        found in the TCGplayer product name.

        The tokenType is assigned based on a defined priority list, where the first
        match found in the name is assigned.
        """
        additional: Dict[str, str | list[str]] = {}

        token_type_priorities: list[tuple[str, str]] = [
            # Highest priority exceptions (Punch/Minigame usually override)
            ("punch", "Punch"),
            ("magic minigame", "Minigame"),
            # Specific token card types
            ("decklist", "Decklist"),
            ("bio", "Bio"),
            ("theme", "Theme"),
            ("art", "Art"),
            ("helper", "Helper"),
            ("world championship", "WorldChampionship"),
            # Tokens/Emblems (the general case)
        ]

        # A keyword has to start a word, so "art" names an art card but not
        # "Earthshaker Khenra" or "Heartwood". "art" must also end one, so
        # "Artifact" or "Artisan" isn't an art card, while "punch" and "bio"
        # still cover "Punchcard" and "Biography".
        for keyword, token_type in token_type_priorities:
            word_end = r"\b" if keyword == "art" else ""
            if re.search(rf"\b{re.escape(keyword)}{word_end}", tcgplayer_token_name_lower):
                additional["tokenType"] = token_type
                break

        if "tokenType" not in additional and any(
            x in tcgplayer_token_name_lower for x in ["token", "emblem"]
        ):
            additional["tokenType"] = "Token"

        if "gold-stamped" in tcgplayer_token_name_lower:
            if "faceAttribute" not in additional:
                additional["faceAttribute"] = []
            additional["faceAttribute"].append("Gold Stamped")

        return additional

    def split_tcgplayer_token_faces_details(
        self,
        tcgplayer_token: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        token_face_names = self.__get_token_face_names(tcgplayer_token["name"])
        first_face_id, second_face_id = None, None
        for raw_extended_data in tcgplayer_token["extendedData"]:
            if raw_extended_data["name"] == "Number":
                if "//" in raw_extended_data["value"]:
                    first_face_id, second_face_id = list(
                        map(str.strip, raw_extended_data["value"].split("//"))
                    )
                else:
                    first_face_id = (
                        raw_extended_data["value"]
                        .split("//")[0]
                        .split("/")[0]
                        .lstrip("0")
                    )

        additional_side_a = {}
        additional_side_b = {}
        additional = self.get_additional_dict(tcgplayer_token["name"].lower())

        if match := self.__treatment_single_side_regex.match(tcgplayer_token["name"]):
            if match.group(1) and "Foil" in match.group(1):
                if "faceAttribute" not in additional_side_a:
                    additional_side_a["faceAttribute"] = []
                additional_side_a["faceAttribute"].append(match.group(1))
            if match.group(2) and "Foil" in match.group(2):
                if "faceAttribute" not in additional_side_b:
                    additional_side_b["faceAttribute"] = []
                additional_side_b["faceAttribute"].append(match.group(2))
        if match := self.__treatment_double_side_regex.match(tcgplayer_token["name"]):
            if "Foil" in match.group(1):
                if "faceAttribute" not in additional:
                    additional["faceAttribute"] = []
                additional["faceAttribute"].append(match.group(1))

        if len(token_face_names) == 2:
            # One number on a two-faced product numbers both of its faces, as
            # with "Day // Night" or the OTJ Bounty cards. A product with no
            # number at all may name each face's number instead.
            if second_face_id is None:
                first_name_number, second_name_number = (
                    self.__get_face_numbers_from_name(tcgplayer_token["name"])
                )
                if first_face_id is None:
                    first_face_id = first_name_number
                    second_face_id = second_name_number
                else:
                    second_face_id = second_name_number or first_face_id
            faces = [
                {
                    "faceName": token_face_names[0],
                    "faceId": first_face_id,
                    **additional,
                    **additional_side_a,
                },
                {
                    "faceName": token_face_names[1],
                    "faceId": second_face_id,
                    **additional,
                    **additional_side_b,
                },
            ]
            hints = self.__get_face_set_code_hints(tcgplayer_token["name"])
            power_toughness = self.__get_face_power_toughness(tcgplayer_token)
            rules_texts = self.__get_face_rules_texts(tcgplayer_token, token_face_names)
            for face, hint, face_power_toughness, rules_text in zip(
                faces, hints, power_toughness, rules_texts
            ):
                if hint:
                    face["setCodeHint"] = hint
                if face_power_toughness:
                    face["powerToughnessHint"] = face_power_toughness
                if rules_text:
                    face["rulesTextHint"] = rules_text
            return faces

        return [
            {
                "faceName": token_face_names[0],
                "faceId": first_face_id,
                **additional,
            }
        ]

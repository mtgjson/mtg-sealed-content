from typing import List, Any, Dict
import re


class TcgplayerTokenParser:
    __emblem_regex: re.Pattern
    __double_sided_token_regex: re.Pattern

    def __init__(self) -> None:
        self.__emblem_regex = re.compile(r"Emblem - (.*)")
        self.__double_sided_token_regex = re.compile(r"^(.*) [Dd]oubled?[- ][Ss]ided")
        self.__treatment_single_side_regex = re.compile(
            r".*?(?:\((.*)\))? // .*?(?:\((.*)\))? [Dd]oubled?[- ][Ss]ided"
        )
        self.__treatment_double_side_regex = re.compile(
            r".*[Dd]oubled?[- ][Ss]ided Token \((.*?)\)"
        )
        self.__role_regex = re.compile(r"(.*) Role / (.*) Role")

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
            if match := self.__double_sided_token_regex.match(token_name):
                left, right = [
                    part.split(" (")[0] for part in match.group(1).split(" // ")
                ]

                left = left.strip()
                right = right.strip()

                if match := self.__role_regex.match(left):
                    left = f"{match.group(1)} // {match.group(2)}"
                if match := self.__role_regex.match(right):
                    right = f"{match.group(1)} // {match.group(2)}"

                return [
                    self.__fix_emblem_names(left),
                    self.__fix_emblem_names(right),
                ]

        if "(" in token_name:
            token_name = token_name.split(" (", 1)[0]
        if "Art Card" in token_name:
            return [token_name.split(" Art Card")[0]]
        if "(Art Series)" in token_name:
            return [token_name.split(" (Art Series)")[0]]
        if "Theme Card" in token_name:
            return [token_name.split(" Theme Card")[0]]
        if "Magic Minigame" in token_name:
            return [token_name.split("Magic Minigame: ")[-1]]

        return [self.__fix_emblem_names(token_name.split(" Token")[0])]

    @staticmethod
    def get_additional_dict(tcgplayer_token_name_lower) -> Dict[str, str | list[str]]:
        additional = {}
        if "punch" in tcgplayer_token_name_lower:
            additional["tokenType"] = "Punch"
        if "magic minigame" in tcgplayer_token_name_lower:
            additional["tokenType"] = "Minigame"
        elif "helper" in tcgplayer_token_name_lower:
            additional["tokenType"] = "Helper"
        elif "art" in tcgplayer_token_name_lower:
            additional["tokenType"] = "Art"
        elif "theme" in tcgplayer_token_name_lower:
            additional["tokenType"] = "Theme"
        elif "bio" in tcgplayer_token_name_lower:
            additional["tokenType"] = "Bio"
        elif "decklist" in tcgplayer_token_name_lower:
            additional["tokenType"] = "Decklist"
        elif any([x in tcgplayer_token_name_lower for x in ["token", "emblem"]]):
            additional["tokenType"] = "Token"
        elif "world championship" in tcgplayer_token_name_lower:
            additional["tokenType"] = "WorldChampionship"

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

        # Hack to account for the Bounty tokens
        if token_face_names[0].startswith("Bounty:"):
            second_face_id = first_face_id

        if len(token_face_names) == 2:
            return [
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

        return [
            {
                "faceName": token_face_names[0],
                "faceId": first_face_id,
                **additional,
            }
        ]

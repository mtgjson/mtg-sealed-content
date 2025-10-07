from typing import List, Any, Dict
import re


class TcgplayerTokenParser:
    __emblem_regex: re.Pattern
    __double_sided_token_regex: re.Pattern

    def __init__(self) -> None:
        self.__emblem_regex = re.compile(r"Emblem - (.*)")
        self.__double_sided_token_regex = re.compile(r"^(.*) [Dd]ouble[- ][Ss]ided")

    def __fix_emblem_names(self, token) -> str:
        if match := self.__emblem_regex.match(token):
            return match.group(1) + " Emblem"
        return token

    def __get_token_face_names(self, token_name: str) -> List[str]:
        if token_name.lower().startswith(("punch card", "punchcard")):
            return ["Punchcard", "Punchcard"]

        if " // " in token_name:
            if match := self.__double_sided_token_regex.match(token_name):
                left, right = [
                    part.split(" (")[0] for part in match.group(1).split(" // ")
                ]
                return [
                    self.__fix_emblem_names(left.strip()),
                    self.__fix_emblem_names(right.strip()),
                ]

        if "(" in token_name:
            token_name = token_name.split(" (", 1)[0]
        return [self.__fix_emblem_names(token_name.split(" Token")[0])]

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
                    first_face_id = raw_extended_data["value"].split("//")[0]

        if len(token_face_names) == 2:
            return [
                {
                    "faceName": token_face_names[0],
                    "faceId": first_face_id,
                },
                {
                    "faceName": token_face_names[1],
                    "faceId": second_face_id,
                },
            ]

        return [
            {
                "faceName": token_face_names[0],
                "faceId": first_face_id,
            }
        ]

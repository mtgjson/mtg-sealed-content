from typing import List, Optional, Any, Dict
import re


class TcgplayerTokenParser:
    __emblem_regex: re.Pattern
    __get_all_face_names_regex: re.Pattern
    __get_punch_card_regex: re.Pattern

    def __init__(self) -> None:
        self.__emblem_regex = re.compile(r"Emblem - (.*)")
        self.__get_all_face_names_regex = re.compile(
            r"^(.*?)(?: \(.*?\))? // (.*?)(?: \(.*?\))? Double[- ]Sided Token.*"
        )
        self.__get_punch_card_regex = re.compile(r"^Punch ?Card Token.*")

    def __fix_emblem_names(self, tokens: List[Optional[str]]) -> None:
        for index, token in enumerate(tokens):
            if token:
                if match := self.__emblem_regex.match(token):
                    tokens[index] = match.group(1) + " Emblem"

    def __get_token_face_names(self, token_name: str) -> List[str]:
        """
        NAME_1A NAME_1B (ID_1) // NAME_2A NAME_2B (ID_2) Double-Sided Token Extra Data Here
        NAME_1A NAME_1B // NAME_2A NAME_2B (ID_2) Double-Sided Token Extra Data Here
        NAME_1A NAME_1B (ID_1) // NAME_2A NAME_2B Double-Sided Token Extra Data Here
        NAME_1A NAME_1B // NAME_2A NAME_2B Double-Sided Token Extra Data Here
        Punch Card Token (ID_1 // ID_2)
        """

        if match := self.__get_all_face_names_regex.match(token_name):
            results = [match.group(1), match.group(2)]
            self.__fix_emblem_names(results)
            return results

        if self.__get_punch_card_regex.match(token_name):
            return ["Punchcard", "Punchcard"]

        try:
            return [token_name.split(" Token")[0]]
        except IndexError:
            return [token_name]

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

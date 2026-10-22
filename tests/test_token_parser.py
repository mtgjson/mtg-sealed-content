import unittest

from scripts.tokens.mtgjson_to_tcgplayer_mapper import MtgjsonToTcgplayerMapper
from scripts.tokens.tcgplayer_token_parser import TcgplayerTokenParser


def rules_text_hints(name, oracle_text):
    faces = TcgplayerTokenParser().split_tcgplayer_token_faces_details(
        {
            "name": name,
            "extendedData": [
                {"name": "Number", "value": "1 // 2"},
                {"name": "OracleText", "value": oracle_text},
            ],
        }
    )
    return [
        MtgjsonToTcgplayerMapper.rules_text_key(face["rulesTextHint"])
        if "rulesTextHint" in face
        else None
        for face in faces
    ]


class RulesTextHintTests(unittest.TestCase):
    def test_faces_split_on_the_separator_without_the_name(self):
        self.assertEqual(
            rules_text_hints(
                "Angel // Soldier Double-Sided Token",
                "<strong>Angel</strong>\r\n<br>\r\nFlying\r\n<br>//<br>\r\n"
                "<strong>Soldier</strong>\r\n<br>\r\nLifelink",
            ),
            ["flying", "lifelink"],
        )

    def test_a_named_face_takes_the_text_after_its_name(self):
        self.assertEqual(
            rules_text_hints(
                "Zombie Army // Zombie (005) Double-Sided Token",
                "<strong>Zombie</strong>\r\n<br>\r\nDecayed",
            ),
            [None, "decayed"],
        )

    def test_text_before_the_back_name_is_the_front(self):
        self.assertEqual(
            rules_text_hints(
                "Inkling // Treasure Double-Sided Token",
                "Flying\r\n<br>\r\n<strong>Treasure</strong><br>\r\n"
                "T, Sacrifice this token: Add one mana of any color.",
            ),
            ["flying", "t sacrifice this token add one mana of any color"],
        )

    def test_text_no_face_claims_is_left_out(self):
        self.assertEqual(rules_text_hints("Bird // Cat Double-Sided Token", "Flying"), [None, None])

    def test_faces_with_one_name_are_left_out(self):
        self.assertEqual(
            rules_text_hints(
                "Zombie (005 MIC) // Zombie (005 MID) Double-Sided Token",
                "<strong>Zombie</strong>\r\n<br>\r\nDecayed",
            ),
            [None, None],
        )

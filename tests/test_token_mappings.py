from copy import deepcopy
import unittest

from scripts.tokens.main import (
    build_tokens_mapping,
    filter_tokens_without_uuids,
    map_uuids_back_to_single_uuid,
)
from scripts.tokens.tcgplayer_token_parser import TcgplayerTokenParser


def token(uuid, name, number):
    return {"uuid": uuid, "name": name, "number": number, "layout": "token"}


def product(name, number, group_id):
    return {
        "productId": 1,
        "groupId": group_id,
        "name": name,
        "extendedData": [{"name": "Number", "value": number}],
    }


class ProductSetTokenMappingTests(unittest.TestCase):
    def build(self, mtgjson_tokens, tcgplayer_product, set_code_to_group_id):
        return build_tokens_mapping(
            "DFT",
            mtgjson_tokens,
            [tcgplayer_product],
            TcgplayerTokenParser(),
            set_code_to_group_id,
        )

    def test_commander_product_pairs_the_commander_token(self):
        mapping = self.build(
            {
                "DFT": [token("dft-zombie", "Zombie", "3")],
                "DRC": [
                    token("drc-dragon", "Timeless Dragon", "6"),
                    token("drc-zombie", "Zombie", "3"),
                ],
            },
            product("Timeless Dragon // Zombie (0003) Double-Sided Token", "6 // 3", 23929),
            {"DFT": 23874, "DRC": 23929},
        )
        self.assertNotIn("dft-zombie", mapping)
        self.assertEqual(
            mapping["drc-dragon"][0]["tokenParts"],
            [{"uuid": "drc-dragon"}, {"uuid": "drc-zombie"}],
        )

    def test_set_named_on_a_face_decides_that_face(self):
        mapping = self.build(
            {
                "MID": [token("mid-zombie", "Zombie", "5")],
                "MIC": [token("mic-zombie", "Zombie", "5")],
            },
            product("Zombie (005 MIC) // Zombie (005 MID) Double-Sided Token", "5 // 5", 2893),
            {"MID": 2864, "MIC": 2893},
        )
        self.assertEqual(
            mapping["mic-zombie"][0]["tokenParts"],
            [{"uuid": "mic-zombie"}, {"uuid": "mid-zombie"}],
        )


class TokenMappingTests(unittest.TestCase):
    def test_ambiguous_face_resolves_to_one_token_and_preserves_input(self):
        tokens = [{"tokenParts": [
            {"uuids": ["A", "B"], "tokenType": "token", "faceId": "front", "faceName": "Front"},
            {"uuids": ["C"], "tokenType": "token", "faceId": "back", "faceName": "Back"},
        ]}]
        original = deepcopy(tokens)
        mapped = map_uuids_back_to_single_uuid(filter_tokens_without_uuids(tokens))
        self.assertEqual(set(mapped), {"A", "C"})
        self.assertEqual(mapped["A"][0]["tokenParts"], [{"uuid": "A"}, {"uuid": "C"}])
        self.assertEqual(mapped["C"][0]["tokenParts"], [{"uuid": "A"}, {"uuid": "C"}])
        self.assertEqual(tokens, original)

    def test_single_face_product_is_listed_under_every_match(self):
        tokens = [{"tokenParts": [{"uuids": ["A", "B"], "tokenType": "Art"}]}]
        mapped = map_uuids_back_to_single_uuid(filter_tokens_without_uuids(tokens))
        self.assertEqual(set(mapped), {"A", "B"})
        self.assertEqual(mapped["A"][0]["tokenParts"], [{"uuid": "A"}])
        self.assertEqual(mapped["B"][0]["tokenParts"], [{"uuid": "B"}])

    def test_same_uuid_on_both_faces_is_not_duplicated(self):
        tokens = [{"tokenParts": [{"uuids": ["A"]}, {"uuids": ["A"]}]}]
        mapped = map_uuids_back_to_single_uuid(filter_tokens_without_uuids(tokens))
        self.assertEqual(len(mapped["A"]), 1)
        self.assertEqual(mapped["A"][0]["tokenParts"], [{"uuid": "A"}, {"uuid": "A"}])

    def test_unmatched_product_is_omitted(self):
        self.assertEqual(filter_tokens_without_uuids([{"tokenParts": [{}]}]), {})

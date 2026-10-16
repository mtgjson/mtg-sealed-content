from copy import deepcopy
import unittest

from scripts.tokens.main import filter_tokens_without_uuids, map_uuids_back_to_single_uuid


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

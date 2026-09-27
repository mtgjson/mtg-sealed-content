from copy import deepcopy
import unittest

from scripts.tokens.main import filter_tokens_without_uuids, map_uuids_back_to_single_uuid
from scripts.tokens.mtgjson_to_tcgplayer_mapper import MtgjsonToTcgplayerMapper


class TokenMappingTests(unittest.TestCase):
    def test_each_uuid_gets_its_own_face_and_preserves_input(self):
        tokens = [{"tokenParts": [
            {"uuids": ["A", "B"], "tokenType": "token", "faceId": "front", "faceName": "Front"},
            {"uuids": ["C"], "tokenType": "token", "faceId": "back", "faceName": "Back"},
        ]}]
        original = deepcopy(tokens)
        mapped = map_uuids_back_to_single_uuid(filter_tokens_without_uuids(tokens))
        self.assertEqual(mapped["A"][0]["tokenParts"], [{"uuid": "A"}, {"uuid": "C"}])
        self.assertEqual(mapped["B"][0]["tokenParts"], [{"uuid": "B"}, {"uuid": "C"}])
        self.assertEqual(mapped["C"][0]["tokenParts"], [{"uuid": "A"}, {"uuid": "C"}])
        self.assertEqual(tokens, original)

    def test_same_uuid_on_both_faces_is_not_duplicated(self):
        tokens = [{"tokenParts": [{"uuids": ["A"]}, {"uuids": ["A"]}]}]
        mapped = map_uuids_back_to_single_uuid(filter_tokens_without_uuids(tokens))
        self.assertEqual(len(mapped["A"]), 1)
        self.assertEqual(mapped["A"][0]["tokenParts"], [{"uuid": "A"}, {"uuid": "A"}])

    def test_unmatched_product_is_omitted(self):
        self.assertEqual(filter_tokens_without_uuids([{"tokenParts": [{}]}]), {})


def _token(uuid, name, number, **extra):
    token = {"uuid": uuid, "name": name, "number": number, "layout": "token"}
    token.update(extra)
    return token


class CandidateResolutionTests(unittest.TestCase):
    """
    Each case is a real collision taken from outputs/token_products_mappings.
    """

    def resolve(self, tokens_by_set, face_id, **kwargs):
        index = MtgjsonToTcgplayerMapper.build_uuid_index(tokens_by_set)
        return MtgjsonToTcgplayerMapper.resolve_candidate_uuids(
            list(index), index, face_id, **kwargs
        )

    def test_product_group_picks_the_set_the_product_came_from(self):
        # TCGplayer 249869 is a MID product; MIC has its own Zombie #5.
        tokens = {
            "MID": [_token("mid-zombie", "Zombie", "5")],
            "MIC": [_token("mic-zombie", "Zombie", "5")],
        }
        self.assertEqual(
            self.resolve(
                tokens,
                "5",
                product_group_id=2864,
                set_code_to_group_id={"MID": 2864, "MIC": 2893},
            ),
            ["mid-zombie"],
        )
        self.assertEqual(
            self.resolve(
                tokens,
                "5",
                product_group_id=2893,
                set_code_to_group_id={"MID": 2864, "MIC": 2893},
            ),
            ["mic-zombie"],
        )

    def test_unknown_group_leaves_both_candidates(self):
        tokens = {
            "MID": [_token("mid-zombie", "Zombie", "5")],
            "MIC": [_token("mic-zombie", "Zombie", "5")],
        }
        self.assertEqual(
            len(self.resolve(tokens, "5", product_group_id=99999,
                             set_code_to_group_id={"MID": 2864, "MIC": 2893})),
            2,
        )

    def test_star_number_is_the_separately_sold_foil_printing(self):
        # 40K Soldier #4 and #4* both answer to TCGplayer face id "4".
        tokens = {
            "40K": [
                _token("plain", "Soldier", "4", finishes=["nonfoil"]),
                _token("surge", "Soldier", "4★", finishes=["foil"]),
            ]
        }
        self.assertEqual(self.resolve(tokens, "4"), ["plain"])
        self.assertEqual(self.resolve(tokens, "4", prefers_foil=True), ["surge"])

    def test_exact_number_beats_a_prefix_stripped_one(self):
        # PLST numbers collapse to the same suffix once the prefix is dropped.
        tokens = {
            "PLST": [
                _token("afr-angel", "Angel", "TAFR-1"),
                _token("grn-angel", "Angel", "TGRN-1"),
            ]
        }
        self.assertEqual(self.resolve(tokens, "TAFR-1"), ["afr-angel"])
        self.assertEqual(len(self.resolve(tokens, "1")), 2)

    def test_two_sided_token_resolves_to_its_front(self):
        # Both halves carry the same combined name and number.
        tokens = {
            "WOE": [
                _token("front", "Monster // Sorcerer", "15",
                       layout="flip", side="a"),
                _token("back", "Monster // Sorcerer", "15",
                       layout="flip", side="b"),
            ]
        }
        self.assertEqual(self.resolve(tokens, "15"), ["front"])

    def test_different_tokens_are_never_collapsed_by_the_side_rule(self):
        # Same set, same number, different cards: nothing here is a tiebreak.
        tokens = {
            "MID": [
                _token("bat", "Bat", "4"),
                _token("zombie", "Zombie", "4"),
            ]
        }
        self.assertEqual(len(self.resolve(tokens, "4")), 2)

    def test_candidate_whose_number_does_not_match_the_face_is_dropped(self):
        tokens = {
            "MID": [
                _token("bat", "Bat", "4"),
                _token("other-bat", "Bat", "9"),
            ]
        }
        self.assertEqual(self.resolve(tokens, "4"), ["bat"])

    def test_number_rank_orders_the_mangling_steps(self):
        rank = MtgjsonToTcgplayerMapper.number_match_rank
        self.assertEqual(rank("4", "4"), 0)
        self.assertEqual(rank("4s", "4"), 1)
        self.assertEqual(rank("4★", "4"), 2)
        self.assertEqual(rank("TAFR-1", "1"), 4)
        self.assertIsNone(rank("4", "5"))
        self.assertIsNone(rank("", "5"))

    def test_gold_stamped_art_card_is_its_own_printing(self):
        # AMH2 #50 and #50s are the plain and gold-stamped signature art cards.
        tokens = {
            "AMH2": [
                _token("plain", "Ethersworn Sphinx // Ethersworn Sphinx", "50",
                       layout="art_series", side="a",
                       finishes=["nonfoil", "signed"], promoTypes=None),
                _token("stamped", "Ethersworn Sphinx // Ethersworn Sphinx", "50s",
                       layout="art_series", side="a",
                       finishes=["nonfoil", "signed"], promoTypes=["stamped"]),
            ]
        }
        self.assertEqual(self.resolve(tokens, "50"), ["plain"])
        self.assertEqual(self.resolve(tokens, "50", prefers_stamped=True), ["stamped"])

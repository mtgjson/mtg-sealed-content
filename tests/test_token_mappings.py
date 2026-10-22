from copy import deepcopy
import unittest

from scripts.tokens.main import (
    build_tokens_mapping,
    filter_tokens_without_uuids,
    map_uuids_back_to_single_uuid,
)
from scripts.tokens.tcgplayer_token_parser import TcgplayerTokenParser


def token(uuid, name, number, power=None, toughness=None):
    return {
        "uuid": uuid,
        "name": name,
        "number": number,
        "layout": "token",
        "power": power,
        "toughness": toughness,
    }


def product(name, number, group_id, power=None, toughness=None, oracle_text=None):
    extended_data = [{"name": "Number", "value": number}]
    if power is not None:
        extended_data += [{"name": "P", "value": power}, {"name": "T", "value": toughness}]
    if oracle_text is not None:
        extended_data.append({"name": "OracleText", "value": oracle_text})
    return {
        "productId": 1,
        "groupId": group_id,
        "name": name,
        "extendedData": extended_data,
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

    def test_power_and_toughness_pick_a_parent_set_back_on_a_commander_product(self):
        mapping = self.build(
            {
                "DFT": [token("dft-zombie", "Zombie", "3", "2", "2")],
                "DRC": [
                    token("drc-warrior", "Zombie Warrior", "9", "4", "4"),
                    token("drc-zombie", "Zombie", "3", "1", "1"),
                ],
            },
            product(
                "Zombie Warrior // Zombie (0003) Double-Sided Token", "9 // 3", 23929, "4/2", "4/2"
            ),
            {"DFT": 23874, "DRC": 23929},
        )
        self.assertNotIn("drc-zombie", mapping)
        self.assertEqual(
            mapping["drc-warrior"][0]["tokenParts"],
            [{"uuid": "drc-warrior"}, {"uuid": "dft-zombie"}],
        )

    def test_rules_text_picks_the_printing_on_a_face(self):
        mapping = self.build(
            {
                "PLST": [
                    token("wolf", "Wolf", "TMID-13", "2", "2"),
                    token("cmr-soldier", "Soldier", "TCMR-2", "1", "1"),
                    {**token("grn-soldier", "Soldier", "TGRN-2", "1", "1"), "text": "Lifelink"},
                ],
            },
            product(
                "Wolf // Soldier Double-Sided Token",
                "13 // 2",
                2715,
                "2/1",
                "2/1",
                "Lifelink\r\n<br>//<br>\r\n<strong>Soldier</strong>\r\n<br>\r\nLifelink",
            ),
            {"PLST": 2715},
        )
        self.assertNotIn("cmr-soldier", mapping)
        self.assertEqual(
            mapping["wolf"][0]["tokenParts"], [{"uuid": "wolf"}, {"uuid": "grn-soldier"}]
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


def face_token(uuid, name, number, face_name, side, layout="double_faced_token"):
    return {**token(uuid, name, number), "layout": layout, "faceName": face_name, "side": side}


class UnmatchedFaceTests(unittest.TestCase):
    def parts(self, mtgjson_tokens, name, number, group_id=1):
        mapping = build_tokens_mapping(
            "SET", mtgjson_tokens, [product(name, number, group_id)], TcgplayerTokenParser()
        )
        return {uuid: entries[0]["tokenParts"] for uuid, entries in mapping.items()}

    def test_art_inside_a_word_does_not_make_an_art_card(self):
        parts = self.parts(
            {"HOU": [token("khenra", "Earthshaker Khenra", "4"), token("cat", "Cat", "16")]},
            "Earthshaker Khenra // Cat Double-Sided Token",
            "4 // 16",
        )
        self.assertEqual(parts["khenra"], [{"uuid": "khenra"}, {"uuid": "cat"}])

    def test_token_word_on_a_face_is_ignored(self):
        parts = self.parts(
            {"MH3": [token("clue", "Clue", "30"), token("energy", "Energy Reserve", "36")]},
            "Clue Token // Energy Reserve Double-Sided Token",
            "30 // 36",
        )
        self.assertEqual(parts["clue"], [{"uuid": "clue"}, {"uuid": "energy"}])

    def test_token_word_in_the_mtgjson_name_is_ignored(self):
        parts = self.parts(
            {"FRC": [token("ginger", "Gingerbrute Token", "12"), token("map", "Map", "14")]},
            "Gingerbrute // Map Double-Sided Token",
            "12 // 14",
        )
        self.assertEqual(parts["ginger"], [{"uuid": "ginger"}, {"uuid": "map"}])

    def test_face_names_match_regardless_of_case(self):
        parts = self.parts(
            {"SOC": [token("primo", "Primo, the Indivisible", "24"), token("t", "Treasure", "12")]},
            "Primo, The Indivisible // Treasure Double-Sided Token",
            "24 // 12",
        )
        self.assertEqual(parts["primo"], [{"uuid": "primo"}, {"uuid": "t"}])

    def test_faces_of_one_double_faced_token_share_its_number(self):
        parts = self.parts(
            {"MID": [
                face_token("day", "Day // Night", "19", "Day", "a"),
                face_token("night", "Day // Night", "19", "Night", "b"),
            ]},
            "Day // Night Double-Sided Token",
            "19",
        )
        self.assertEqual(parts["day"], [{"uuid": "day"}, {"uuid": "night"}])

    def test_face_matches_one_side_of_a_double_faced_token(self):
        parts = self.parts(
            {"FRC": [
                face_token("incubator", "Incubator // Phyrexian", "13", "Incubator", "a"),
                face_token("phyrexian", "Incubator // Phyrexian", "13", "Phyrexian", "b"),
            ]},
            "Phyrexian // Incubator Double-Sided Token",
            "13 // 13",
        )
        self.assertEqual(parts["phyrexian"], [{"uuid": "phyrexian"}, {"uuid": "incubator"}])

    def test_numbers_listed_in_the_other_order_still_match(self):
        parts = self.parts(
            {"LCI": [token("map", "Map", "17"), token("treasure", "Treasure", "18")]},
            "Treasure (0018) // Map Double-Sided Token",
            "17 // 18",
        )
        self.assertEqual(parts["treasure"], [{"uuid": "treasure"}, {"uuid": "map"}])

    def test_numbers_in_face_names_stand_in_for_a_missing_number(self):
        mapping = build_tokens_mapping(
            "UNF",
            {"UNF": [
                token("robot-2", "Clown Robot", "2"),
                token("robot-3", "Clown Robot", "3"),
                token("food-10", "Food", "10"),
                token("food-11", "Food", "11"),
            ]},
            [{"productId": 1, "groupId": 1, "extendedData": [],
              "name": "Clown Robot (003) // Food (011) Double-sided Token"}],
            TcgplayerTokenParser(),
        )
        self.assertEqual(
            mapping["robot-3"][0]["tokenParts"], [{"uuid": "robot-3"}, {"uuid": "food-11"}]
        )

    def test_unnumbered_face_matches_the_only_token_with_its_name(self):
        mapping = build_tokens_mapping(
            "UNF",
            {"UNF": [token("cat", "Cat", "1"), token("food-10", "Food", "10")]},
            [{"productId": 1, "groupId": 2958, "extendedData": [],
              "name": "Cat // Food (10) Double-sided Token"}],
            TcgplayerTokenParser(),
            {"UNF": 2958, "SUNF": 2958},
        )
        self.assertEqual(mapping["cat"][0]["tokenParts"], [{"uuid": "cat"}, {"uuid": "food-10"}])

    def test_unnumbered_face_needs_a_token_from_the_set_selling_it(self):
        mapping = build_tokens_mapping(
            "BRO",
            {"BRO": [token("bear", "Bear", "2")]},
            [{"productId": 1, "groupId": 2351, "extendedData": [], "name": "Bear Token"}],
            TcgplayerTokenParser(),
            {"BRO": 3157, "PTSNC": 2351},
        )
        self.assertEqual(mapping, {})

    def test_unnumbered_single_token_is_not_matched_by_name(self):
        mapping = build_tokens_mapping(
            "MKM",
            {"WMKM": [token("zombie", "Zombie", "1")]},
            [{"productId": 1, "groupId": 2351, "extendedData": [], "name": "Zombie Token"}],
            TcgplayerTokenParser(),
            {"WMKM": 2351, "PTSNC": 2351},
        )
        self.assertEqual(mapping, {})

    def test_theme_card_matches_a_front_card(self):
        front = {**token("shield", "Agents of S.H.I.E.L.D.", "11"), "layout": "front_card"}
        parts = self.parts({"FMSC": [front]}, "Agents of S.H.I.E.L.D. Theme Card", "11")
        self.assertEqual(parts["shield"], [{"uuid": "shield"}])

    def test_swapped_numbers_must_match_both_faces(self):
        parts = self.parts(
            {"SET": [token("zombie", "Zombie", "21")]},
            "Treasure (021) // Zombie Double-Sided Token",
            "21 // 6",
        )
        self.assertEqual(parts, {})

    def test_art_card_with_another_number_does_not_match_a_longer_name(self):
        def art(uuid, name, number):
            return {**token(uuid, f"{name} // {name}", number), "layout": "art_series", "side": "b"}

        parts = self.parts(
            {"ATLA": [art("swamp", "Swamp", "52")], "ATLE": [art("benders", "Swampbenders", "4")]},
            "Swamp Art Card",
            "52",
        )
        self.assertEqual(set(parts), {"swamp"})

    def test_art_card_can_shorten_the_name_when_the_numbers_agree(self):
        art = {
            **token("tyrant", "Ghastly Death Tyrant // Ghastly Death Tyrant", "11"),
            "layout": "art_series",
            "side": "b",
        }
        parts = self.parts({"ACLB": [art]}, "Death Tyrant Art Card", "11")
        self.assertEqual(set(parts), {"tyrant"})

    def test_single_role_token_matches_its_two_roles(self):
        roles = [
            face_token("royal", "Royal // Young Hero", "16", "Royal", "a", "flip"),
            face_token("hero", "Royal // Young Hero", "16", "Young Hero", "b", "flip"),
        ]
        parts = self.parts({"WOE": roles}, "Royal Role / Young Hero Role Token", "16")
        self.assertEqual(set(parts), {"royal", "hero"})

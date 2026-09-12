import contextlib
from copy import deepcopy
import io
import unittest

from scripts.card_to_product_compiler import MtgjsonCardLinker, results_to_json
from scripts.product_classes import card


class CardToProductMappingTests(unittest.TestCase):
    def test_direct_card_finishes_preserve_etched_precedence(self):
        for flags, expected in (
            ({}, "nonfoil"), ({"foil": True}, "foil"),
            ({"etched": True}, "etched"),
            ({"foil": True, "etched": True}, "etched"),
            ({"foil": True, "etched": False}, "foil"),
        ):
            with self.subTest(flags=flags):
                # Exercise the card representation produced by this repo.
                content = card({"name": "Example", "set": "tst", "number": 1,
                                "uuid": "card-id", **flags}).toJson()
                mapped = MtgjsonCardLinker.get_card_obj_from_card(content)
                self.assertEqual([(entry.uuid, entry.finish) for entry in mapped], [("card-id", expected)])

    def test_unresolved_etched_card_is_omitted(self):
        self.assertEqual(MtgjsonCardLinker.get_card_obj_from_card({"etched": True}), [])

    def test_nested_configurations_map_all_content_types_and_keep_finishes(self):
        linker = MtgjsonCardLinker.__new__(MtgjsonCardLinker)
        nested = {"configs": [{
            "card": [{"uuid": "shared", "etched": True}, {"uuid": "shared", "foil": True}],
            "sealed": [{"set": "tst", "uuid": "child"}],
            "deck": [{"set": "tst", "name": "Example Deck"}],
            "pack": [{"set": "tst", "code": "default"}],
            "other": [{"name": "Accessories"}],
            "card_count": 10,
            "variable_config": [{"chance": 1, "weight": 2}],
            "variable": [{"configs": [{"card": [{"uuid": "deep", "etched": True}]}]}],
        }]}
        linker.mtgjson_data = {"TST": {
            "sealedProduct": [
                {"uuid": "parent", "name": "Parent", "contents": {
                    "card": [{"uuid": "shared"}],
                    "variable": [{"configs": [{"variable": [nested]}, {"variable": [deepcopy(nested)]}]}],
                }},
                {"uuid": "child", "name": "Child", "contents": {"card": [{"uuid": "child-card", "etched": True}]}},
            ],
            "cards": [{"uuid": "deck-card", "finishes": ["nonfoil"]}], "tokens": [],
            "decks": [{"name": "Example Deck", "sourceSetCodes": ["TST"], "cards": [{"uuid": "deck-card"}]}],
            "booster": {"default": {
                "boosters": [{"contents": {"common": 1}}],
                "sheets": {"common": {"foil": False, "cards": {"pack-card": 1}}},
            }},
        }}
        original = deepcopy(linker.mtgjson_data)
        with contextlib.redirect_stdout(io.StringIO()):
            mapped = results_to_json(linker.build(None, False))
        self.assertEqual(mapped, {
            "shared": {"nonfoil": ["parent"], "foil": ["parent"], "etched": ["parent"]},
            "deep": {"etched": ["parent"]},
            "child-card": {"etched": ["child", "parent"]},
            "deck-card": {"nonfoil": ["parent"]},
            "pack-card": {"nonfoil": ["parent"]},
        })
        self.assertEqual(linker.mtgjson_data, original)

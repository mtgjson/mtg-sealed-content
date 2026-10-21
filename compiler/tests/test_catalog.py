import copy
import unittest

from mtg_sealed_choices.catalog import CatalogWalker
from mtg_sealed_choices.links import CardReference
from mtg_sealed_choices.uuid_map import uuid_map_from_events


def events(value, prefix=""):
    """A tiny standard-JSON event source, independent of optional ijson."""
    if isinstance(value, dict):
        yield prefix, "start_map", None
        for key, child in value.items():
            yield prefix, "map_key", key
            yield from events(child, f"{prefix}.{key}" if prefix else key)
        yield prefix, "end_map", None
    elif isinstance(value, list):
        yield prefix, "start_array", None
        for child in value:
            yield from events(child, f"{prefix}.item")
        yield prefix, "end_array", None
    else:
        yield prefix, "string", value


class CatalogTests(unittest.TestCase):
    def test_uuid_parser_faces_collisions_and_set_boundaries(self):
        data = {
            "data": {
                "TST": {
                    "booster": {"default": {"sheets": {"ignored": {}}}},
                    "decks": [{"name": "Deck"}],
                    "sealedProduct": [{"uuid": "p", "name": "Product"}],
                    "cards": [
                        {"number": "1", "uuid": "front", "name": "Front", "side": "a"},
                        {"side": "b", "number": "1", "uuid": "back", "name": "Back"},
                        {"number": "2", "uuid": "single", "name": "Single", "foreignData": [{"name": "Ignore"}]},
                    ],
                    "tokens": [{"number": "1", "uuid": "token", "name": "Token"}],
                },
                "END": {"cards": []},
            }
        }
        result = uuid_map_from_events(events(data))
        self.assertEqual(
            result["tst"],
            {
                "booster": {"default"},
                "decks": {"Deck"},
                "sealedProduct": {"Product": "p"},
                "cards": {"1": ("front", "Front"), "2": ("single", "Single")},
                "tokens": {"1": ("token", "Token")},
            },
        )
        self.assertEqual(result["end"]["cards"], {})

    def test_only_reachable_sheets_and_adapter_finish_corrections(self):
        class Legacy(CatalogWalker):
            def extra_pack_finishes(self, source_code, card):
                return {"etched"} if source_code == "TST" else set()

        sheet = {"foil": True, "cards": {"card": 1}}
        data = {
            "TST": {
                "cards": [{"uuid": "card", "finishes": ["nonfoil", "foil"]}],
                "booster": {
                    "default": {
                        "sourceSetCodes": ["TST"],
                        "boosters": [{"contents": {"foil": 1}}],
                        "sheets": {"foil": sheet, "unused": {"foil": False, "cards": {"unused": 1}}},
                    }
                },
            }
        }
        original = copy.deepcopy(data)
        self.assertEqual(set(CatalogWalker(data).get_cards_in_pack("TST", "default")), {CardReference("card", "foil")})
        self.assertEqual(
            set(Legacy(data).get_cards_in_pack("TST", "default")),
            {CardReference("card", "foil"), CardReference("card", "etched")},
        )
        self.assertEqual(data, original)

    def test_nested_product_language_is_not_inherited(self):
        class Languages(CatalogWalker):
            def product_language(self, product):
                return product.get("language")

            def deck_card_uuid(self, card, language, set_code, deck_name):
                return language or card["uuid"]

        data = {
            "TST": {
                "cards": [{"uuid": "english", "finishes": ["foil", "etched"]}],
                "tokens": [],
                "decks": [
                    {
                        "name": "Deck",
                        "sourceSetCodes": ["TST"],
                        "mainBoard": [{"uuid": "english", "isEtched": True, "isFoil": True}],
                    }
                ],
                "sealedProduct": [
                    {
                        "uuid": "parent",
                        "language": "Japanese",
                        "contents": {
                            "card_count": 2,
                            "variable": [
                                {
                                    "configs": [
                                        {
                                            "deck": [{"set": "tst", "name": "Deck"}],
                                            "sealed": [{"set": "tst", "uuid": "child"}],
                                        }
                                    ]
                                }
                            ],
                        },
                    },
                    {"uuid": "child", "contents": {"deck": [{"set": "tst", "name": "Deck"}]}},
                ],
            }
        }
        self.assertEqual(
            set(Languages(data).get_cards_in_sealed_product("TST", "parent")),
            {CardReference("Japanese", "etched"), CardReference("english", "etched")},
        )

    def test_missing_and_unknown_references(self):
        walker = CatalogWalker({})
        self.assertEqual(walker.get_cards_in_pack("TST", "missing"), [])
        self.assertEqual(walker.get_cards_in_deck("TST", "missing"), [])
        self.assertEqual(walker.get_cards_in_sealed_product("TST", "missing"), [])
        with self.assertRaisesRegex(ValueError, "Unknown content_key"):
            walker.get_cards_in_content_type("bad", {})


if __name__ == "__main__":
    unittest.main()

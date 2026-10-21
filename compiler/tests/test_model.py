import unittest
from mtg_sealed_choices.model import Card, Product, deck_links
from mtg_sealed_choices.links import explicit_card, variable_cards, deck_cards, results_to_json


class RecipeTests(unittest.TestCase):
    def test_nested_resolution_and_adapter_hooks(self):
        seen = []

        class ResolvedCard(Card):
            def get_uuids(self, mapping):
                seen.append(self.name)
                self.uuid = mapping[self.name]

        class ResolvedProduct(Product):
            card_type = ResolvedCard

            def resolve_uuid(self, mapping):
                self.uuid = mapping.get(self.name)

        recipe = ResolvedProduct(
            {"variable": [{"variable": [{"card": [{"name": "Nested", "number": 1, "set": "TST", "foil": True}]}]}]},
            "TST",
            "Pack",
        )
        recipe.get_uuids({"Nested": "card-id", "Pack": "pack-id"})
        self.assertEqual(seen, ["Nested"])
        card = recipe.toJson()["variable"][0]["configs"][0]["variable"][0]["configs"][0]["card"][0]
        self.assertEqual(card, {"name": "Nested", "number": "1", "set": "TST", "foil": True, "uuid": "card-id"})

    def test_shared_links_and_metadata(self):
        def resolve(kind, entry):
            if kind == "variable":
                return variable_cards(entry, resolve)
            return explicit_card(entry) if kind == "card" else []

        result = variable_cards(
            {
                "configs": [
                    {
                        "card_count": 2,
                        "variable_config": [{"chance": 1}],
                        "variable": [{"configs": [{"card": [{"uuid": "a", "etched": True, "foil": True}]}]}],
                        "card": [{"uuid": "a", "etched": True}],
                    }
                ]
            },
            resolve,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(results_to_json({result[0]: {"z", "b"}}), {"a": {"etched": ["b", "z"]}})
        self.assertEqual(
            deck_cards({"tokens": [{"uuid": "t"}], "planarDeck": [{"uuid": "p"}]}), [{"uuid": "t"}, {"uuid": "p"}]
        )

    def test_direct_deck_links_exclude_unresolved_products(self):
        one = Product({"deck": [{"set": "TST", "name": "Deck"}]})
        two = Product({"deck": [{"set": "TST", "name": "Deck"}]})
        one.uuid = "one"
        self.assertEqual(deck_links({"TST": {"one": one, "two": two}}), {"TST": {"Deck": ["one"]}})


if __name__ == "__main__":
    unittest.main()

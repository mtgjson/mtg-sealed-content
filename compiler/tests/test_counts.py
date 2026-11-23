import unittest

from mtg_sealed_choices.counts import booster_card_count, deck_card_count
from mtg_sealed_choices.model import Card, Deck, Pack, Product, Sealed


class DeckCardCountTests(unittest.TestCase):
    def assert_formats(self, source, compiled, expected):
        for label, deck in (("source", source), ("compiled", compiled)):
            with self.subTest(format=label):
                self.assertEqual(deck_card_count(deck), expected)

    def test_commander_excludes_display_card(self):
        self.assert_formats(
            {"cards": {
                "Main Deck": [{"count": 99}],
                "Commander": [{"count": 1}],
                "Display Commander": [{"count": 1}],
            }},
            {"cards": [{"count": 99}], "commander": [{"count": 1}],
             "displayCommander": [{"count": 1}]},
            100,
        )

    def test_tokens_do_not_inflate_secret_lair_count(self):
        self.assert_formats(
            {"cards": {"Main Deck": [
                {"count": 8}, {"count": 1, "token": True},
            ]}},
            {"cards": [{"count": 8}], "tokens": [{"count": 1}]},
            8,
        )

    def test_includes_sideboard(self):
        self.assert_formats(
            {"cards": {"Main Deck": [{"count": 60}],
                       "Sideboard": [{"count": 15}]}},
            {"cards": [{"count": 60}], "sideboard": [{"count": 15}]},
            75,
        )

    def test_includes_planar_and_scheme_decks(self):
        for source_name, compiled_name in (
            ("Planar Deck", "planarDeck"), ("Scheme Deck", "schemeDeck"),
        ):
            with self.subTest(section=source_name):
                self.assert_formats(
                    {"cards": {"Main Deck": [{"count": 60}],
                               source_name: [{"count": 10}]}},
                    {"cards": [{"count": 60}], compiled_name: [{"count": 10}]},
                    70,
                )

    def test_scene_box_without_extra_sections(self):
        self.assert_formats(
            {"cards": {"Main Deck": [{"count": 1} for _ in range(6)]}},
            {"cards": [{"count": 1} for _ in range(6)]},
            6,
        )

    def test_token_only_deck_counts_its_tokens(self):
        self.assert_formats(
            {"cards": {"Main Deck": [{"count": 2, "token": True}, {"count": 3, "token": True}]}},
            {"cards": [], "tokens": [{"count": 2}, {"count": 3}]},
            5,
        )


class BoosterCardCountTests(unittest.TestCase):
    def test_reads_the_size_most_weight_opens_to(self):
        config = {"boosters": [
            {"weight": 3, "contents": {"common": 10, "uncommon": 3, "rare": 1}},
            {"weight": 1, "contents": {"common": 10, "uncommon": 3, "rare": 1, "bonus": 1}},
        ]}
        self.assertEqual(booster_card_count(config), 14)

    def test_tie_takes_the_larger_size(self):
        config = {"boosters": [
            {"weight": 1, "contents": {"common": 14}},
            {"weight": 1, "contents": {"common": 15}},
        ]}
        self.assertEqual(booster_card_count(config), 15)

    def test_no_boosters_has_no_size(self):
        self.assertIsNone(booster_card_count({"boosters": []}))


class SizedPack(Pack):
    def get_uuids(self, sizes):
        self.card_count = sizes.get(self.code)


class SizedDeck(Deck):
    def get_uuids(self, sizes):
        self.card_count = sizes.get(self.name)


class Unresolved:
    def get_uuids(self, sizes):
        pass


class SizedProduct(Product):
    card_type = type("UnresolvedCard", (Unresolved, Card), {})
    pack_type = SizedPack
    deck_type = SizedDeck
    sealed_type = type("UnresolvedSealed", (Unresolved, Sealed), {})


SIZES = {"draft": 15, "Deck": 60, "Other Deck": 40}


def counted(contents):
    product = SizedProduct(contents, "tst", "Product")
    product.get_uuids(SIZES)
    return product


class ProductCardCountTests(unittest.TestCase):
    def test_counts_cards_packs_and_decks_but_not_nested_sealed(self):
        product = counted({
            "card": [{"set": "tst", "number": 1, "name": "Promo"}],
            "pack": [{"set": "tst", "code": "draft"}],
            "deck": [{"set": "tst", "name": "Deck"}],
            "sealed": [{"set": "tst", "count": 6, "name": "Booster Pack"}],
            "other": [{"name": "Spindown"}],
        })
        self.assertEqual(product.card_count(), 76)
        self.assertEqual(product.toJson()["card_count"], 76)

    def test_ignores_a_card_count_written_in_the_contents(self):
        self.assertEqual(counted({"card_count": 5, "deck": [{"set": "tst", "name": "Deck"}]}).card_count(), 60)

    def test_only_sealed_contents_publish_no_count(self):
        product = counted({"sealed": [{"set": "tst", "count": 36, "name": "Booster Pack"}]})
        self.assertEqual(product.card_count(), 0)
        self.assertNotIn("card_count", product.toJson())

    def test_choice_adds_the_count_its_configs_share(self):
        product = counted({"pack": [{"set": "tst", "code": "draft"}], "variable": [
            {"deck": [{"set": "tst", "name": "Deck"}]},
            {"card": [{"set": "tst", "number": n, "name": "Card"} for n in range(60)]},
        ]})
        self.assertEqual(product.card_count(), 75)
        published = product.toJson()
        self.assertEqual(published["card_count"], 75)
        self.assertEqual(["card_count" in config for config in published["variable"][0]["configs"]], [False, False])

    def test_chosen_combination_sums_its_parts(self):
        product = counted({"variable": [
            {"deck": [{"set": "tst", "name": "Other Deck"}]},
            {"deck": [{"set": "tst", "name": "Other Deck"}]},
        ], "variable_mode": {"count": 2, "replacement": True}})
        self.assertEqual(product.card_count(), 80)

    def test_unsized_pack_or_deck_has_no_count(self):
        for contents in ({"pack": [{"set": "tst", "code": "missing"}]}, {"deck": [{"set": "tst", "name": "Missing"}]}):
            with self.subTest(contents=contents):
                product = counted(contents)
                self.assertIsNone(product.card_count())
                self.assertNotIn("card_count", product.toJson())

    def test_configs_of_different_sizes_have_no_count(self):
        product = counted({"variable": [
            {"deck": [{"set": "tst", "name": "Deck"}]},
            {"deck": [{"set": "tst", "name": "Other Deck"}]},
        ]})
        self.assertIsNone(product.card_count())


if __name__ == "__main__":
    unittest.main()

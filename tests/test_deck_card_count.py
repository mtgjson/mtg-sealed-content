import unittest

from scripts.deck_card_count import deck_card_count


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


if __name__ == "__main__":
    unittest.main()

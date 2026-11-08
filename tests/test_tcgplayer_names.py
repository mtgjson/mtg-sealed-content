import unittest

from scripts.load_new_products import normalize_tcgplayer_name


class TcgplayerNameTests(unittest.TestCase):
    def test_secret_lair_titles_become_product_names(self):
        cases = {
            "Secret Lair Drop Secret Lair x Masters of the Universe She Ra Princess of Power Non Foil Edition":
                "Secret Lair Drop Masters of the Universe She Ra Princess of Power",
            "Secret Lair Drop Secret Lair x Masters of the Universe She Ra Princess of Power Traditional Foil Edition":
                "Secret Lair Drop Masters of the Universe She Ra Princess of Power Foil",
            "Secret Lair x Furby Doo ay Noo lah Confetti Foil Edition":
                "Secret Lair Drop Furby Doo ay Noo lah Confetti Foil",
            "Secret Lair Drop Goblin and Squabblin Rainbow Foil Edition":
                "Secret Lair Drop Goblin and Squabblin Rainbow Foil",
            "Secret Lair Drop Showcase Monster Anatomy 101 Foil Etched Edition":
                "Secret Lair Drop Showcase Monster Anatomy 101 Etched",
            "Secret Lair Drop Seeing Visions Traditional Foil Version":
                "Secret Lair Drop Seeing Visions Foil",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_tcgplayer_name(raw), expected)

    def test_other_products_keep_their_names(self):
        for name in ("Marvel Darkhold Destiny Commander Deck Case Collectors Edition",
                     "Duskmourn: House of Horror Foil Promo Pack"):
            self.assertEqual(normalize_tcgplayer_name(name), name)


if __name__ == "__main__":
    unittest.main()

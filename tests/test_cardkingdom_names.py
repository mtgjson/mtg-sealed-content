import unittest

from scripts.load_new_products import normalize_cardkingdom_name


class CardKingdomNameTests(unittest.TestCase):
    def test_titles_become_product_names(self):
        cases = {
            "Secret Lair Drop - Secret Lair x The Hobbit: Smaug's Spoils - Foil":
                "Secret Lair Drop The Hobbit Smaug's Spoils Foil",
            "Secret Lair Drop - Secret Lair x Masters of the Universe: She-Ra, Princess of Power - Non-Foil":
                "Secret Lair Drop Masters of the Universe She Ra, Princess of Power",
            "Secret Lair Drop - Secret Lair x The Hobbit: He Who Walks Unseen - Out of Sight Foil":
                "Secret Lair Drop The Hobbit He Who Walks Unseen Out of Sight Foil",
            "Chaos Vault - Secret Lair x Marvel: Spinner Rack Specials - Non-Foil":
                "Secret Lair Drop Marvel Spinner Rack Specials",
            "Secret Lair Drop: Tragic Romance - Non-Foil":
                "Secret Lair Drop Tragic Romance",
            "Secret Lair Drop - Artist Series: Chris Rahn - Regular":
                "Secret Lair Drop Artist Series Chris Rahn",
            "Secret Lair Drop - Monster Anatomy 101 - Foil Etched":
                "Secret Lair Drop Monster Anatomy 101 Etched",
            "Secret Lair Drop - Outlaw Anthology Vol.2: Sinister Scoundrels - Non-Foil":
                "Secret Lair Drop Outlaw Anthology Vol 2 Sinister Scoundrels",
            "Universes Beyond: Fallout Commander Deck - Mutant Menace":
                "Fallout Commander Deck Mutant Menace",
            "Tarkir: Dragonstorm - Complete Set (Factory Sealed)":
                "Tarkir Dragonstorm MTGO Redemption",
            "The Brothers' War - Complete FOIL Set (Factory Sealed)":
                "The Brothers' War MTGO Redemption Foil",
            "Mercadian Masques Booster Box":
                "Mercadian Masques Booster Box",
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalize_cardkingdom_name(raw), expected)


if __name__ == "__main__":
    unittest.main()

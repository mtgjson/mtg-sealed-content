import unittest
from scripts.card_to_product_compiler import MtgjsonCardLinker


class CatalogAdapterTests(unittest.TestCase):
    def test_legacy_etched_ranges_remain_adapter_owned(self):
        adapter = MtgjsonCardLinker.__new__(MtgjsonCardLinker)
        for code, number, expected in [
            ("MH2", "261", set()), ("MH2", "262", {"etched"}),
            ("MH2", "441", {"etched"}), ("MH2", "442", set()),
            ("H1R", "1", {"etched"}), ("STA", "1", {"etched"}), ("TST", "1", set()),
        ]:
            with self.subTest(code=code, number=number):
                self.assertEqual(adapter.extra_pack_finishes(code, {"number": number}), expected)


if __name__ == "__main__":
    unittest.main()

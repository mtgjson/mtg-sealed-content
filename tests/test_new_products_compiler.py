import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import new_products_compiler


class NewProductsCompilerTests(unittest.TestCase):
    def compile(self, products):
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            try:
                Path("data/products").mkdir(parents=True)
                Path("outputs").mkdir()
                Path("data/products/TST.yaml").write_text(yaml.safe_dump({"code": "tst", "products": products}))
                new_products_compiler.main()
                return json.loads(Path("outputs/products.json").read_text())
            finally:
                os.chdir(previous)

    def test_always_emits_identifiers_mapping(self):
        # MTGJSON's SealedProduct fails the whole build on missing or null identifiers
        output = self.compile({
            "Missing": {"category": "BOOSTER_PACK", "subtype": "PROMOTIONAL", "contents": {"card_count": 3}},
            "Null": {"category": "BOOSTER_PACK", "subtype": "DEFAULT", "identifiers": None},
            "Known": {"category": "BOOSTER_BOX", "subtype": "DEFAULT", "identifiers": {"tcgplayerProductId": "1"}},
        })
        self.assertEqual(output["tst"]["Missing"], {"category": "BOOSTER_PACK", "subtype": "PROMOTIONAL", "identifiers": {}})
        self.assertEqual(output["tst"]["Null"]["identifiers"], {})
        self.assertEqual(output["tst"]["Known"]["identifiers"], {"tcgplayerProductId": "1"})


if __name__ == "__main__":
    unittest.main()

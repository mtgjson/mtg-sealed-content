import copy
import os
from pathlib import Path
import tempfile
import unittest

import yaml
from scripts import sealed_yaml

BOX = {"category": "BOOSTER_BOX", "subtype": "DEFAULT", "identifiers": {"tcgplayerProductId": "1"}}
BOX_CONTENTS = {"sealed": [{"count": 36, "name": "Pack", "set": "tst"}]}


class SealedYamlTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        previous = Path.cwd()
        os.chdir(self.directory.name)
        self.addCleanup(os.chdir, previous)
        Path("data/products").mkdir(parents=True)

    def write_split(self, products, contents):
        # Independent copies, so the fixture files carry no YAML anchors
        products = {name: copy.deepcopy(value) for name, value in products.items()}
        contents = {name: copy.deepcopy(value) for name, value in contents.items()}
        Path("data/contents").mkdir(exist_ok=True)
        Path("data/products/TST.yaml").write_text(
            yaml.safe_dump({"code": "tst", "products": products}, allow_unicode=True))
        Path("data/contents/TST.yaml").write_text(
            yaml.safe_dump({"code": "tst", "products": contents}, allow_unicode=True))

    def test_split_round_trip_is_byte_identical(self):
        self.write_split(
            {"Box": BOX, "Pack": BOX, "Unresearched": BOX, "Copy": BOX},
            {"Box": BOX_CONTENTS, "Pack": {"card_count": 15}, "Unresearched": [], "Copy": {"copy": "Box"},
             "Leftover": {"card_count": 1}},
        )
        before = [Path(p).read_bytes() for p in ("data/products/TST.yaml", "data/contents/TST.yaml")]
        data = sealed_yaml.load_set("TST")
        self.assertEqual(data["products"]["Box"]["contents"], BOX_CONTENTS)
        self.assertNotIn("contents", data["products"]["Unresearched"])
        sealed_yaml.save_set("TST", data)
        after = [Path(p).read_bytes() for p in ("data/products/TST.yaml", "data/contents/TST.yaml")]
        self.assertEqual(before, after)

    def test_split_save_adds_placeholders_and_drops_empty_leftovers(self):
        self.write_split({"Box": BOX, "New": BOX}, {"Box": BOX_CONTENTS, "Gone": {}})
        sealed_yaml.save_set("TST", sealed_yaml.load_set("TST"))
        contents = yaml.safe_load(Path("data/contents/TST.yaml").read_text())["products"]
        self.assertEqual(contents, {"Box": BOX_CONTENTS, "New": {}})

    def test_merged_layout_nests_contents_last_and_omits_empty_ones(self):
        data = sealed_yaml.new_set("TST")
        data["products"]["Box"] = {**BOX, "contents": BOX_CONTENTS, "release_date": "2020-01-01"}
        data["products"]["Pack"] = {**BOX, "contents": {}}
        sealed_yaml.save_set("TST", data)
        text = Path("data/products/TST.yaml").read_text()
        box = text.split("  Box:\n")[1].split("  Pack:\n")[0]
        keys = [line.strip().split(":")[0] for line in box.splitlines() if line.startswith("    ") and not line.startswith("     ")]
        self.assertEqual(keys, ["category", "subtype", "release_date", "identifiers", "contents"])
        loaded = sealed_yaml.load_set("TST")
        self.assertEqual(loaded["products"]["Box"]["contents"], BOX_CONTENTS)
        self.assertNotIn("contents", loaded["products"]["Pack"])

    def test_writer_rule_refuses_losing_products_or_contents(self):
        self.write_split({"Box": BOX, "Pack": BOX}, {"Box": {**BOX_CONTENTS, "card_count": 36}, "Pack": {}})
        cases = {
            "would drop product 'Pack'": lambda data: data["products"].pop("Pack"),
            "would remove 'sealed'": lambda data: data["products"]["Box"]["contents"].pop("sealed"),
            "would overwrite 'card_count'": lambda data: data["products"]["Box"]["contents"].update(card_count=1),
            # Replacing the whole entry, as import_new_decks used to, loses the contents
            "would remove 'card_count'": lambda data: data["products"].update(Box=dict(BOX)),
        }
        for message, change in cases.items():
            with self.subTest(message):
                data = sealed_yaml.load_set("TST")
                change(data)
                with self.assertRaisesRegex(sealed_yaml.WriterRuleError, message):
                    sealed_yaml.save_set("TST", data)

    def test_writer_rule_allows_additions_and_named_overrides(self):
        self.write_split({"Box": BOX}, {"Box": {**BOX_CONTENTS, "card_count": 36}})
        data = sealed_yaml.load_set("TST")
        data["products"]["Box"]["contents"]["other"] = [{"name": "Rules insert"}]
        data["products"]["Box"]["identifiers"]["mcmId"] = "2"
        data["products"]["New"] = dict(BOX)
        sealed_yaml.save_set("TST", data)

        data = sealed_yaml.load_set("TST")
        data["products"]["Box"]["contents"]["card_count"] = 40
        with self.assertRaises(sealed_yaml.WriterRuleError):
            sealed_yaml.save_set("TST", data, allow={"Box": {"other"}})
        with self.assertRaises(sealed_yaml.WriterRuleError):
            sealed_yaml.save_set("TST", data, allow={"New": {"card_count"}})
        sealed_yaml.save_set("TST", data, allow={"Box": {"card_count"}})
        self.assertEqual(sealed_yaml.load_set("TST")["products"]["Box"]["contents"]["card_count"], 40)

    def test_writer_rule_keeps_filled_contents_entries_without_a_product(self):
        self.write_split({"Box": BOX}, {"Box": {}, "Leftover": {"card_count": 1}})
        data = sealed_yaml.load_set("TST")
        data.pop("_orphans")
        with self.assertRaisesRegex(sealed_yaml.WriterRuleError, "'Leftover', which has no product"):
            sealed_yaml.save_set("TST", data)

    def test_layout_errors(self):
        self.assertEqual(sealed_yaml.layout_errors(), [])  # merged: nothing to reconcile
        self.write_split({"Box": BOX, "New": BOX, "Nested": {**BOX, "contents": BOX_CONTENTS}},
                         {"Box": {}, "Nested": {}, "Leftover": {"card_count": 1}})
        Path("data/products/NEW.yaml").write_text(yaml.safe_dump({"code": "new", "products": {}}))
        Path("data/contents/OLD.yaml").write_text(yaml.safe_dump({"code": "old", "products": {}}))
        errors = "\n".join(sealed_yaml.layout_errors())
        self.assertIn("data/contents/OLD.yaml has no data/products/OLD.yaml", errors)
        self.assertIn("data/products/NEW.yaml has no data/contents/NEW.yaml", errors)
        self.assertIn("product 'New' has no entry", errors)
        self.assertIn("contents entry 'Leftover' has no product", errors)
        self.assertIn("product 'Nested' nests contents", errors)


if __name__ == "__main__":
    unittest.main()

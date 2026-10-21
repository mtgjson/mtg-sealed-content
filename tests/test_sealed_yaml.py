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

    def write(self, products):
        # Independent copies, so the fixture file carries no YAML anchors
        products = {name: copy.deepcopy(value) for name, value in products.items()}
        Path("data/products/TST.yaml").write_text(
            yaml.safe_dump({"code": "tst", "products": products}, allow_unicode=True))

    def test_save_nests_contents_last_and_omits_empty_ones(self):
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

    def test_resave_is_byte_identical(self):
        data = sealed_yaml.new_set("TST")
        data["products"]["Box"] = {**BOX, "contents": BOX_CONTENTS}
        data["products"]["Copy"] = {**BOX, "contents": {"copy": "Box"}}
        data["products"]["Unresearched"] = dict(BOX)
        sealed_yaml.save_set("TST", data)
        before = Path("data/products/TST.yaml").read_bytes()
        sealed_yaml.save_set("TST", sealed_yaml.load_set("TST"))
        self.assertEqual(Path("data/products/TST.yaml").read_bytes(), before)

    def test_writer_rule_refuses_losing_products_or_contents(self):
        self.write({"Box": {**BOX, "contents": {**BOX_CONTENTS, "card_count": 36}}, "Pack": BOX})
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
        self.write({"Box": {**BOX, "contents": {**BOX_CONTENTS, "card_count": 36}}})
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

    def test_layout_errors_flag_a_returning_data_contents_file(self):
        self.write({"Box": {**BOX, "contents": BOX_CONTENTS}})
        self.assertEqual(sealed_yaml.layout_errors(), [])
        Path("data/contents").mkdir()
        self.assertEqual(sealed_yaml.layout_errors(), [])  # an empty directory is harmless
        Path("data/contents/TST.yaml").write_text(yaml.safe_dump({"code": "tst", "products": {"Box": {}}}))
        errors = sealed_yaml.layout_errors()
        self.assertEqual(len(errors), 1)
        self.assertIn("data/contents/ is no longer read, but it has TST.yaml", errors[0])


if __name__ == "__main__":
    unittest.main()

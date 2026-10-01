import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest

import yaml
from scripts import convert_layout, sealed_yaml

BOX = {"category": "BOOSTER_BOX", "subtype": "DEFAULT", "identifiers": {}}
PRODUCTS = {"Box": BOX, "Copy": BOX, "Pack": BOX, "Unresearched": BOX, "Variable": BOX}
CONTENTS = {
    "Box": {"sealed": [{"count": 36, "name": "Pack", "set": "tst"}]},
    "Copy": {"copy": "Box"},
    "Pack": {"card_count": 15, "pack": [{"code": "draft", "set": "tst"}]},
    "Unresearched": [],
    "Variable": {"variable": [{"card_count": 1}, {"card_count": 2}], "variable_mode": {"count": 1}},
}


class ConvertLayoutTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        previous = Path.cwd()
        os.chdir(self.directory.name)
        self.addCleanup(os.chdir, previous)
        Path("data/products").mkdir(parents=True)
        Path("data/contents").mkdir()
        for code in ("TST", "TWO"):
            Path(f"data/products/{code}.yaml").write_text(
                yaml.safe_dump({"code": code.lower(), "products": PRODUCTS}, allow_unicode=True))
            Path(f"data/contents/{code}.yaml").write_text(
                yaml.safe_dump({"code": code.lower(), "products": CONTENTS}, allow_unicode=True))

    def run_command(self, *argv):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            convert_layout.main(list(argv))
        return output.getvalue()

    def test_merge_then_split_restores_the_data(self):
        before = {code: sealed_yaml.load_set(code) for code in ("TST", "TWO")}
        self.assertIn("round-trip cleanly from the split layout", self.run_command("check"))

        self.run_command("merge")
        self.assertFalse(Path("data/contents").exists())
        merged = yaml.safe_load(Path("data/products/TST.yaml").read_text())["products"]
        self.assertEqual(merged["Copy"]["contents"], {"copy": "Box"})
        self.assertNotIn("contents", merged["Unresearched"])
        self.assertIn("round-trip cleanly from the merged layout", self.run_command("check"))

        self.run_command("split")
        for code, data in before.items():
            self.assertEqual(sealed_yaml.load_set(code)["products"], data["products"])
        # The only change a round trip makes: [] placeholders come back as {}
        contents = yaml.safe_load(Path("data/contents/TST.yaml").read_text())["products"]
        self.assertEqual(contents, {**CONTENTS, "Unresearched": {}})

    def test_merge_refuses_names_out_of_sync(self):
        Path("data/contents/TST.yaml").write_text(
            yaml.safe_dump({"code": "tst", "products": {**CONTENTS, "Renamed away": {"card_count": 1}}}))
        with self.assertRaises(SystemExit), contextlib.redirect_stdout(io.StringIO()):
            convert_layout.main(["merge"])
        self.assertTrue(Path("data/contents/TST.yaml").exists())

    def test_fold_applies_a_branch_contents_file_to_a_merged_tree(self):
        self.run_command("merge")
        Path("data/contents").mkdir()
        branch = {**CONTENTS, "Unresearched": {"card_count": 3}, "Pack": {}}
        Path("data/contents/TST.yaml").write_text(yaml.safe_dump({"code": "tst", "products": branch}))
        self.run_command("fold", "TST")
        self.assertFalse(Path("data/contents").exists())
        products = sealed_yaml.load_set("TST")["products"]
        self.assertEqual(products["Unresearched"]["contents"], {"card_count": 3})
        self.assertNotIn("contents", products["Pack"])
        self.assertEqual(products["Box"]["contents"], CONTENTS["Box"])

    def test_fold_refuses_a_fully_split_tree(self):
        with self.assertRaises(SystemExit):
            convert_layout.main(["fold", "TST"])


if __name__ == "__main__":
    unittest.main()

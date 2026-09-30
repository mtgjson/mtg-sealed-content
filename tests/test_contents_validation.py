import contextlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest

import yaml
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from contents_validator import validate_content_fields, validate_structure


BOX = {"category": "BOOSTER_BOX", "subtype": "DEFAULT", "identifiers": {}}


class ContentsValidationTests(unittest.TestCase):
    def test_rejects_unknown_fields_and_invalid_counts_recursively(self):
        for content in (
            {"crad": []}, {"card count": 30},
            {"sealed": [{"name": "Box", "set": "tst", "count": -1}]},
            {"sealed": [{"name": "Box", "set": "tst", "count": True}]},
            {"card": [{"name": "Card", "set": "tst", "number": 1, "fiol": True}]},
            {"variable": [{"crad": []}]},
            {"variable": [], "variable_mode": {"count": 0}},
            {"variable": [], "variable_mode": {"replacement": "false"}},
        ):
            with self.subTest(content=content), self.assertRaises(ValueError):
                validate_content_fields(content)

    def test_accepts_placeholders_and_variable_contents(self):
        for content in (None, [], {}, {"card_count": 0}, {
            "variable": [{"sealed": [{"name": "Box", "set": "tst", "count": 2}]}],
            "variable_mode": {"count": 1, "replacement": False, "weight": 1},
        }):
            validate_content_fields(content)

    def run_gate(self, products, contents=None):
        """Run the CI gate on one set, split when `contents` is given, merged otherwise.
        Returns (passed, output)."""
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            try:
                Path("data/products").mkdir(parents=True)
                Path("data/products/TST.yaml").write_text(yaml.safe_dump({"code": "tst", "products": products}))
                if contents is not None:
                    Path("data/contents").mkdir()
                    Path("data/contents/TST.yaml").write_text(yaml.safe_dump({"code": "tst", "products": contents}))
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    try:
                        validate_structure()
                    except (ImportError, ValueError):
                        return False, output.getvalue()
                return True, output.getvalue()
            finally:
                os.chdir(previous)

    def test_ci_gate_rejects_typo_in_copied_content(self):
        passed, output = self.run_gate(
            {"Original": BOX, "Copy": BOX},
            {"Original": {"crad": []}, "Copy": {"copy": "Original"}},
        )
        self.assertFalse(passed)
        self.assertIn("crad", output)

    def test_ci_gate_accepts_both_layouts(self):
        contents = {"sealed": [{"name": "Pack", "set": "tst", "count": 36}]}
        self.assertEqual(self.run_gate({"Box": BOX, "Pack": BOX}, {"Box": contents, "Pack": {}})[0], True)
        self.assertEqual(self.run_gate({"Box": {**BOX, "contents": contents}, "Pack": BOX})[0], True)

    def test_ci_gate_rejects_names_out_of_sync_in_either_direction(self):
        # A filled contents entry left behind by a one-sided rename...
        passed, output = self.run_gate({"Renamed": BOX}, {"Renamed": {}, "Original": {"card_count": 1}})
        self.assertFalse(passed)
        self.assertIn("contents entry 'Original' has no product", output)
        # ...and a product with no contents entry at all
        passed, output = self.run_gate({"Box": BOX, "New": BOX}, {"Box": {}})
        self.assertFalse(passed)
        self.assertIn("product 'New' has no entry", output)

    def test_ci_gate_points_misplaced_content_fields_to_the_right_place(self):
        passed, output = self.run_gate({"Box": {**BOX, "sealed": []}})
        self.assertFalse(passed)
        self.assertIn("belongs under `contents:`", output)
        passed, output = self.run_gate({"Box": {**BOX, "sealed": []}}, {"Box": {}})
        self.assertFalse(passed)
        self.assertIn("belongs in data/contents/TST.yaml", output)
        passed, output = self.run_gate({"Box": {**BOX, "purchase_url": "x"}})
        self.assertFalse(passed)
        self.assertIn("unknown field `purchase_url`", output)

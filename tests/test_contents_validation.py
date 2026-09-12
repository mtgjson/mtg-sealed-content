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

    def test_ci_gate_rejects_typo_in_copied_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            try:
                Path("data/contents").mkdir(parents=True)
                Path("data/products").mkdir()
                Path("data/contents/TST.yaml").write_text(yaml.safe_dump({
                    "code": "tst", "products": {"Original": {"crad": []}, "Copy": {"copy": "Original"}},
                }))
                with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ImportError):
                    validate_structure()
            finally:
                os.chdir(previous)

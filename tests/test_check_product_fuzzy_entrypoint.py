import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class FuzzyEntrypointTests(unittest.TestCase):
    def run_python(self, arguments, directory):
        return subprocess.run(
            [sys.executable, *arguments], cwd=directory,
            env={**os.environ, 'PYTHONPATH': str(ROOT)},
            text=True, capture_output=True, timeout=20,
        )


    def test_imports_do_not_fetch_read_data_or_prompt(self):
        code = '''
import argparse
import importlib
import requests
import yaml
from thefuzz import fuzz
from unittest.mock import patch
from pathlib import Path
with patch('requests.sessions.Session.request', side_effect=AssertionError('network')), \\
     patch('builtins.open', side_effect=AssertionError('file access')), \\
     patch.object(Path, 'open', side_effect=AssertionError('path access')), \\
     patch.object(Path, 'glob', side_effect=AssertionError('directory scan')), \\
     patch('builtins.input', side_effect=AssertionError('prompt')), \\
     patch.object(argparse.ArgumentParser, 'parse_args', side_effect=AssertionError('CLI parsing')):
    for name in ('check_product_fuzzy',):
        module = importlib.import_module('scripts.' + name)
        assert callable(module.main)
'''
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_python(['-c', code], directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')


    def test_fuzzy_cli_still_applies_match(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'data/products').mkdir(parents=True)
            name = 'Example Set Collector Booster Box'
            path = base / 'data/products/TST.yaml'
            path.write_text(yaml.safe_dump({'code': 'tst', 'products': {
                name: {'category': 'BOOSTER_BOX', 'subtype': 'COLLECTOR', 'identifiers': {}},
            }}))
            review = base / 'data/review.yaml'
            review.write_text(yaml.safe_dump({'vendor': {name: {'identifiers': {'vendorId': '123'}}}}))
            result = self.run_python([str(ROOT / 'scripts/check_product_fuzzy.py'), '--auto'], directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(yaml.safe_load(path.read_text())['products'][name]['identifiers'], {'vendorId': '123'})
            self.assertEqual(yaml.safe_load(review.read_text()), {'vendor': {}})


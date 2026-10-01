import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class DeckEntrypointTests(unittest.TestCase):
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
    for name in ('import_new_decks',):
        module = importlib.import_module('scripts.' + name)
        assert callable(module.main)
'''
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_python(['-c', code], directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')


    def test_explicit_deck_import_uses_local_source_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'data/products').mkdir(parents=True)
            (base / 'data/contents').mkdir()
            source = base / 'decks.json'
            source.write_text(json.dumps([{
                'name': 'Example', 'set_code': 'tst', 'set_name': 'Test Set',
                'type': 'Theme Deck', 'category': 'Deck', 'release_date': '2020-01-01',
                'cards': [{'count': 60}],
            }]))
            code = '''
import os
from unittest.mock import patch
from scripts.import_new_decks import main
os.environ['DECKS_JSON'] = 'decks.json'
with patch('requests.get', side_effect=AssertionError('unexpected download')):
    main()
    main()
'''
            result = self.run_python(['-c', code], directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            contents = yaml.safe_load((base / 'data/contents/TST.yaml').read_text())['products']
            self.assertEqual(len(contents), 1)
            self.assertEqual(contents['Test Set Theme Deck Example']['card_count'], 60)
            self.assertIn('deck already referenced', result.stdout)

    def test_import_merges_into_an_existing_product(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'data/products').mkdir(parents=True)
            (base / 'data/contents').mkdir()
            name = 'Test Set Theme Deck Example'
            (base / 'data/products/TST.yaml').write_text(yaml.safe_dump({'code': 'tst', 'products': {name: {
                'category': 'UNKNOWN', 'subtype': 'UNKNOWN', 'language': 'German',
                'identifiers': {'tcgplayerProductId': '9'},
            }}}))
            (base / 'data/contents/TST.yaml').write_text(yaml.safe_dump({'code': 'tst', 'products': {name: {
                'other': [{'name': 'Rules insert'}],
            }}}))
            (base / 'decks.json').write_text(json.dumps([{
                'name': 'Example', 'set_code': 'tst', 'set_name': 'Test Set',
                'type': 'Theme Deck', 'category': 'Deck', 'release_date': '2020-01-01',
                'cards': [{'count': 60}],
            }]))
            code = '''
import os
from scripts.import_new_decks import main
os.environ['DECKS_JSON'] = 'decks.json'
main()
'''
            result = self.run_python(['-c', code], directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            product = yaml.safe_load((base / 'data/products/TST.yaml').read_text())['products'][name]
            self.assertEqual(product, {
                'category': 'DECK', 'subtype': 'THEME', 'release_date': '2020-01-01', 'language': 'German',
                'identifiers': {'tcgplayerProductId': '9'},
            })
            contents = yaml.safe_load((base / 'data/contents/TST.yaml').read_text())['products'][name]
            self.assertEqual(contents, {
                'card_count': 60, 'deck': [{'name': 'Example', 'set': 'tst'}], 'other': [{'name': 'Rules insert'}],
            })

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]


class SldEntrypointTests(unittest.TestCase):
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
    for name in ('sld_auto',):
        module = importlib.import_module('scripts.' + name)
        assert callable(module.main)
'''
        with tempfile.TemporaryDirectory() as directory:
            result = self.run_python(['-c', code], directory)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, '')


    def test_explicit_review_still_loads_decks_and_accepts_quit(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            (base / 'data/contents').mkdir(parents=True)
            target = base / 'data/contents/SLD.yaml'
            original = {'code': 'sld', 'products': {f'Product {i}': {} for i in range(5)}}
            target.write_text(yaml.safe_dump(original))
            code = '''
import json
import runpy
import requests
from unittest.mock import patch
response = requests.Response()
response.status_code = 200
response._content = json.dumps({'data': {'decks': [{'name': 'Example', 'mainBoard': [{'count': 1}]}]}}).encode()
with patch('requests.get', return_value=response) as get, patch('builtins.input', return_value='q') as prompt:
    runpy.run_module('scripts.sld_auto', run_name='__main__')
    get.assert_called_once()
    prompt.assert_called_once()
'''
            result = self.run_python(['-c', code], directory)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Finding similar products for Example', result.stdout)
            self.assertEqual(yaml.safe_load(target.read_text()), original)

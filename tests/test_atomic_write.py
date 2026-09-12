import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from scripts.atomic_write import atomic_write


class AtomicWriteTests(unittest.TestCase):
    def test_success_replaces_file_and_preserves_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.json'
            path.write_text('old')
            path.chmod(0o640)
            with atomic_write(path) as stream:
                json.dump({'new': True}, stream)
                self.assertEqual(path.read_text(), 'old')
            self.assertEqual(json.loads(path.read_text()), {'new': True})
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o640)
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_serialization_failure_preserves_old_file_or_absence(self):
        for exists in (True, False):
            with self.subTest(exists=exists), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'data.json'
                if exists:
                    path.write_text('old')
                with self.assertRaises(TypeError), atomic_write(path) as stream:
                    json.dump({'partial': 1, 'invalid': object()}, stream)
                self.assertEqual(path.exists(), exists)
                if exists:
                    self.assertEqual(path.read_text(), 'old')
                self.assertEqual(list(Path(directory).iterdir()), [path] if exists else [])

    def test_replace_failure_preserves_original_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data.json'
            path.write_text('old')
            with patch.object(Path, 'replace', side_effect=OSError('replace failed')), self.assertRaises(OSError):
                with atomic_write(path) as stream:
                    stream.write('new')
            self.assertEqual(path.read_text(), 'old')
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_token_output_survives_failed_serialization(self):
        import os
        from scripts.tokens.main import save_output
        with tempfile.TemporaryDirectory() as directory:
            previous = Path.cwd()
            os.chdir(directory)
            try:
                save_output('TST', {'old': []})
                path = Path('outputs/token_products_mappings/TST.json')
                before = path.read_bytes()
                with self.assertRaises(TypeError):
                    save_output('TST', {'new': object()})
                self.assertEqual(path.read_bytes(), before)
            finally:
                os.chdir(previous)

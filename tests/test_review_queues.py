import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml
from scripts import load_new_products


class ReviewQueueTests(unittest.TestCase):
    def test_skipped_and_failed_queues_survive_successful_refresh(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous = Path.cwd()
            os.chdir(tmp)
            try:
                Path("data/products").mkdir(parents=True)
                Path("data/contents").mkdir()
                Path("data/ignore.yaml").write_text("{}")
                old = {key: {"Pending": {"identifiers": {key: "123"}}}
                       for key in ("skipped", "failed", "active", "unregistered")}
                Path("data/review.yaml").write_text(yaml.safe_dump(old))
                def fail(_):
                    raise RuntimeError("offline")
                providers = {
                    "skipped": {"disabled": True, "identifier": "skipped"},
                    "failed": {"identifier": "failed", "load_func": fail},
                    "active": {"identifier": "active", "load_func": lambda _: [{"name": "New", "id": "456"}]},
                }
                with patch.object(load_new_products, "providers_dict", providers), contextlib.redirect_stdout(io.StringIO()):
                    load_new_products.main({})
                result = yaml.safe_load(Path("data/review.yaml").read_text())
                for key in ("skipped", "failed", "unregistered"):
                    self.assertEqual(result[key], old[key])
                self.assertEqual(set(result["active"]), {"New"})
                self.assertEqual(result["active"]["New"]["identifiers"], {"active": "456"})
            finally:
                os.chdir(previous)

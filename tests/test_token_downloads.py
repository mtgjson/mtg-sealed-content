import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import requests
from scripts.tokens.tcgplayer_provider import TcgplayerProvider


class InlinePool:
    def __init__(self, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def starmap(self, function, args):
        return [function(*item) for item in args]


class TokenDownloadTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.previous = Path.cwd()
        os.chdir(self.temp.name)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(os.chdir, self.previous)
        self.provider = TcgplayerProvider.__new__(TcgplayerProvider)
        self.session = Mock()
        self.provider._TcgplayerProvider__session = self.session
        self.params = {"groupId": 1, "offset": 0, "limit": 100}
        self.cache = Path("caches/tcgplayer/1-0.json")
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def response(self, payload, status=200):
        response = requests.Response()
        response.status_code = status
        response.url = "https://example.test/catalog"
        response._content = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        response._content_consumed = True
        return response

    def download(self):
        return self.provider.download("https://example.test/catalog", self.params)

    def write_cache(self, contents):
        self.cache.parent.mkdir(parents=True, exist_ok=True)
        self.cache.write_text(contents)

    def test_http_and_json_failures_never_create_cache(self):
        for response in (self.response(b"maintenance", 503), self.response(b"not json")):
            with self.subTest(status=response.status_code):
                self.session.get.return_value = response
                with self.assertRaises((requests.HTTPError, ValueError)):
                    self.download()
                self.assertFalse(self.cache.exists())

    def test_invalid_envelopes_never_create_cache(self):
        for payload in ([], {"success": False, "results": []},
                        {"results": []}, {"success": True},
                        {"success": True, "errors": ["partial failure"], "results": []},
                        {"success": True, "results": {}},
                        {"success": True, "results": [None]}):
            with self.subTest(payload=payload):
                self.session.get.return_value = self.response(payload)
                with self.assertRaises(ValueError):
                    self.download()
                self.assertFalse(self.cache.exists())

    def test_valid_catalog_is_cached_and_reused(self):
        products = [{"productId": 1, "name": "Example Token"}]
        self.session.get.return_value = self.response({"success": True, "errors": [], "results": products})
        self.assertEqual(self.download(), products)
        self.assertEqual(json.loads(self.cache.read_text()), products)
        self.assertEqual(self.download(), products)
        self.session.get.assert_called_once_with("https://example.test/catalog", params=self.params)

    def test_legacy_empty_or_corrupt_cache_is_refetched(self):
        products = [{"productId": 1}]
        for old in ("[]", "broken JSON", "{}", "[null]"):
            with self.subTest(old=old):
                self.write_cache(old)
                self.session.get.return_value = self.response({"success": True, "results": products})
                self.assertEqual(self.download(), products)
                self.assertEqual(json.loads(self.cache.read_text()), products)

    def test_failed_refresh_leaves_old_cache_unchanged(self):
        self.write_cache("[]")
        self.session.get.return_value = self.response({"success": False, "results": []})
        with self.assertRaises(ValueError):
            self.download()
        self.assertEqual(self.cache.read_text(), "[]")

    def test_interrupted_cache_write_does_not_publish_partial_file(self):
        self.write_cache("[]")
        self.session.get.return_value = self.response({"success": True, "results": [{"productId": 1}]})
        def fail_write(value, fp, **kwargs):
            fp.write("[")
            raise OSError("disk full")
        with patch("scripts.tokens.tcgplayer_provider.json.dump", side_effect=fail_write), self.assertRaises(OSError):
            self.download()
        self.assertEqual(self.cache.read_text(), "[]")
        self.assertEqual(list(self.cache.parent.iterdir()), [self.cache])

    def test_valid_empty_page_ends_pagination(self):
        self.session.get.return_value = self.response({"success": True, "errors": [], "results": []})
        with patch("scripts.tokens.tcgplayer_provider.multiprocessing.Pool", InlinePool):
            self.assertEqual(self.provider.download_exhaustive("https://example.test/catalog", self.params, threads=1), [])
        self.session.get.assert_called_once()

    def test_failed_later_page_does_not_return_partial_catalog(self):
        self.session.get.side_effect = [
            self.response({"success": True, "results": [{"productId": 1}]}),
            self.response(b"maintenance", 503),
        ]
        with patch("scripts.tokens.tcgplayer_provider.multiprocessing.Pool", InlinePool), self.assertRaises(requests.HTTPError):
            self.provider.download_exhaustive("https://example.test/catalog", self.params, threads=1)
        self.assertTrue(self.cache.exists())
        self.assertFalse(Path("caches/tcgplayer/1-100.json").exists())

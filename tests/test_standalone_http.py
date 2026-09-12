import contextlib
import io
from pathlib import Path
import runpy
import sys
import unittest
from unittest.mock import Mock, patch

import requests
from scripts import load_new_products
from scripts.card_to_product_compiler import MtgjsonCardLinker
from scripts.gatherer_original_printing_details_generator import GathererDownloader

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from contents_validator import build_uuid_map


def response(status, content):
    result = requests.Response()
    result.status_code = status
    result._content = content
    result._content_consumed = True
    result.url = "https://example.test"
    return result


class StandaloneHttpTests(unittest.TestCase):
    def test_error_pages_do_not_become_empty_catalogs(self):
        for loader in (load_new_products.load_miniaturemarket, load_new_products.load_tnt,
                       load_new_products.load_hareruya):
            with self.subTest(loader=loader.__name__), patch.object(
                load_new_products.requests, "get", return_value=response(503, b"maintenance")
            ) as get, contextlib.redirect_stdout(io.StringIO()), self.assertRaises(requests.HTTPError):
                loader(None)
            self.assertEqual(get.call_args.kwargs["timeout"], (10, 60))

    def test_post_search_errors_raise_before_json_parsing(self):
        with patch.object(load_new_products.requests, "post", return_value=response(503, b"maintenance")) as post:
            with self.assertRaises(requests.HTTPError):
                load_new_products.scgbuylistdownload("test", 0, 100)
        self.assertEqual(post.call_args.kwargs["timeout"], (10, 60))
        self.assertEqual(post.call_args.kwargs["json"]["limit"], 100)

    def test_gatherer_failed_second_page_does_not_return_partial_sets(self):
        session = Mock()
        session.get.side_effect = [response(200, b'<a href="/sets/abc">ABC</a>'), response(503, b"maintenance")]
        downloader = GathererDownloader(session)
        with self.assertRaises(requests.HTTPError):
            downloader.get_set_codes()
        self.assertEqual(session.get.call_count, 2)
        self.assertEqual(session.get.call_args.kwargs["timeout"], (10, 60))

    def test_allprintings_timeout_uses_backup(self):
        linker = MtgjsonCardLinker.__new__(MtgjsonCardLinker)
        payload = b'{"data":{"ABC":{"sealedProduct":[{}],"decks":[{}]}}}'
        with patch.object(linker, "PRIMARY_URL", "https://example.test/primary.json"), patch.object(
            linker, "BACKUP_URL", "https://example.test/backup.json"
        ), patch("scripts.card_to_product_compiler.requests.get", side_effect=[requests.Timeout(), response(200, payload)]) as get, contextlib.redirect_stdout(io.StringIO()):
            result = linker._download_mtgjson_data()
        self.assertIn("ABC", result)
        self.assertEqual(get.call_count, 2)
        self.assertEqual(get.call_args.args[0], "https://example.test/backup.json")
        self.assertEqual(get.call_args.kwargs["timeout"], (10, 60))

    def test_status_download_failure_is_not_parsed(self):
        with patch("requests.get", return_value=response(503, b'{"data":{}}')), patch("ijson.parse") as parse, contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(build_uuid_map(None))
        parse.assert_not_called()

    def test_deck_import_download_failure_stops_before_writing(self):
        root = Path(__file__).resolve().parents[1]
        with patch.dict("os.environ", {"DECKS_JSON": ""}), patch("requests.get", return_value=response(503, b"[]")), patch("builtins.open", side_effect=AssertionError("unexpected file access")), patch("pathlib.Path.glob", return_value=[]), self.assertRaises(requests.HTTPError):
            runpy.run_path(str(root / "scripts/import_new_decks.py"), run_name="__main__")

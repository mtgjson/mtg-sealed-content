from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import requests
from urllib3.exceptions import MaxRetryError
from requests.adapters import BaseAdapter
from scripts.retryable_session import retryable_session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from scryfall_provider import ScryfallProvider


class RecordingAdapter(BaseAdapter):
    def send(self, request, **kwargs):
        self.timeout = kwargs["timeout"]
        response = requests.Response()
        response.status_code = 200
        response._content = b"{}"
        return response

    def close(self):
        pass


class HttpReliabilityTests(unittest.TestCase):
    def test_default_timeout_and_caller_override_reach_transport(self):
        with retryable_session() as session:
            adapter = RecordingAdapter()
            session.mount("https://", adapter)
            session.get("https://example.test")
            self.assertEqual(adapter.timeout, (10, 60))
            session.get("https://example.test", timeout=7)
            self.assertEqual(adapter.timeout, 7)

    def test_transient_status_retries_are_bounded_and_exclude_post(self):
        with retryable_session(retries=2) as session:
            retry = session.get_adapter("https://").max_retries
            for status in (429, 500, 502, 503, 504):
                self.assertTrue(retry.is_retry("GET", status))
                self.assertFalse(retry.is_retry("POST", status))
            self.assertFalse(retry.is_retry("GET", 401))
            retry = retry.increment(method="GET", error=Exception("offline"))
            retry = retry.increment(method="GET", error=Exception("offline"))
            with self.assertRaises(MaxRetryError):
                retry.increment(method="GET", error=Exception("offline"))

    def response(self, payload, status=200):
        response = requests.Response()
        response.status_code = status
        response._content = payload
        response._content_consumed = True
        response.url = "https://example.test"
        return response

    def download(self, outcomes):
        session = Mock()
        session.__enter__ = Mock(return_value=session)
        session.__exit__ = Mock(return_value=False)
        session.get.side_effect = outcomes
        return session, patch("scryfall_provider.retryable_session", return_value=session)

    @patch("scryfall_provider.time.sleep")
    def test_invalid_json_exhausts_budget(self, sleep):
        session, factory = self.download([self.response(b"blocked") for _ in range(3)])
        with factory, self.assertRaises(ValueError):
            ScryfallProvider().download("https://example.test", retry_ttl=2)
        self.assertEqual(session.get.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        session.__exit__.assert_called_once()

    @patch("scryfall_provider.time.sleep")
    def test_mixed_body_failures_share_budget_and_preserve_params(self, sleep):
        session, factory = self.download([
            requests.exceptions.ChunkedEncodingError("interrupted"),
            self.response(b"not json"), self.response(b'{"data": []}'),
        ])
        with factory:
            result = ScryfallProvider().download("https://example.test", {"q": "test"}, retry_ttl=2)
        self.assertEqual(result, {"data": []})
        self.assertEqual(session.get.call_count, 3)
        session.get.assert_called_with("https://example.test", params={"q": "test"})

    def test_empty_search_404_is_preserved_but_other_http_errors_raise(self):
        session, factory = self.download([self.response(b'{"object":"error","code":"not_found"}', 404)])
        with factory:
            self.assertEqual(ScryfallProvider().download("https://example.test")["code"], "not_found")
        session, factory = self.download([self.response(b'{"error":"unauthorized"}', 401)])
        with factory, self.assertRaises(requests.HTTPError):
            ScryfallProvider().download("https://example.test")
        self.assertEqual(session.get.call_count, 1)

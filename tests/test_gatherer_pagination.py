import unittest
from unittest.mock import Mock

import requests

from scripts.gatherer_original_printing_details_generator import GathererDownloader


def make_response(status_code, body=b""):
    response = requests.Response()
    response.status_code = status_code
    response._content = body
    response.url = "https://gatherer.wizards.com/test"
    return response


class GathererPaginationTests(unittest.TestCase):
    def test_404_after_last_set_page_ends_pagination(self):
        pages = {
            1: make_response(200, b'<a href="/AL/en-us/1/a">A</a>'),
            2: make_response(200, b'<a href="/AL/en-us/2/b">B</a>'),
        }
        session = Mock(headers={})
        session.get.side_effect = lambda url, **kwargs: pages.get(
            int(url.rsplit("=", 1)[-1]), make_response(404)
        )

        urls = GathererDownloader(session).get_card_urls_from_set_code("AL")

        self.assertEqual(
            urls,
            [
                "https://gatherer.wizards.com/AL/en-us/1/a",
                "https://gatherer.wizards.com/AL/en-us/2/b",
            ],
        )

    def test_404_on_first_set_page_is_still_an_error(self):
        session = Mock(headers={})
        session.get.return_value = make_response(404)

        with self.assertRaises(requests.HTTPError):
            GathererDownloader(session).get_card_urls_from_set_code("AL")


if __name__ == "__main__":
    unittest.main()

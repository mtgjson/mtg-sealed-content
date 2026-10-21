import unittest
from unittest import mock

from scripts.tokens.all_printings import AllPrintings
from scripts.tokens.mtgjson_parser import MtgjsonParser


class FakeAllPrintings(AllPrintings):
    def __init__(self, data):
        self._AllPrintings__temp_file_data = {"data": data}

    def __del__(self):
        pass


def token_set(code, parent=None):
    return {"code": code, "parentCode": parent, "tokens": [{"uuid": code}]}


def parser_for(*sets):
    data = {s["code"]: {k: v for k, v in s.items() if v is not None} for s in sets}
    with mock.patch(
        "scripts.tokens.mtgjson_parser.AllPrintings", lambda: FakeAllPrintings(data)
    ):
        return MtgjsonParser()


class AssociatedTokenSetTests(unittest.TestCase):
    def test_tokens_of_a_child_of_a_child_set_are_included(self):
        parser = parser_for(
            token_set("MSH"), token_set("MSC", "MSH"), token_set("FMSC", "MSC")
        )
        self.assertEqual(
            set(parser.get_associated_mtgjson_tokens("MSH")), {"MSH", "MSC", "FMSC"}
        )

    def test_tokens_paired_from_another_set_are_included(self):
        parser = parser_for(token_set("C20"), token_set("IKO"))
        self.assertEqual(set(parser.get_associated_mtgjson_tokens("C20")), {"C20", "IKO"})

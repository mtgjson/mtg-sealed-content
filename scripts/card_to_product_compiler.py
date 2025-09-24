import argparse
import json
import pathlib
from collections import defaultdict
from typing import Any, Dict, Set, List
import requests


class Card:
    uuid: str
    finish: str

    def __init__(self, uuid: str, finish: str):
        self.uuid = uuid
        self.finish = finish

    def __hash__(self):
        return hash((self.uuid, self.finish))

    def __eq__(self, other: Any):
        if not isinstance(other, Card):
            return False
        return self.uuid == other.uuid and self.finish == other.finish


class MtgjsonCardLinker:
    mtgjson_data: Dict[str, Any]

    def __init__(self, mtgjson_path: str):
        if mtgjson_path:
            print("Loading local AllPrintings.json")
            with open(mtgjson_path) as f:
                self.mtgjson_data = json.load(f).get("data")
            return

        print("Downloading latest AllPrintings.json")
        _all_printings_url = "https://mtgjson.com/api/v5/AllPrintings.json"
        request_wrapper = requests.get(_all_printings_url)

        self.mtgjson_data = json.loads(request_wrapper.content).get("data")

    def build(self, code: str) -> Dict[Card, Set[str]]:
        return_value = defaultdict(set)

        set_codes = self.mtgjson_data.items()
        if code:
            set_codes = [(code.upper(), self.mtgjson_data.get(code.upper()))]

        for set_code, set_data in set_codes:
            if not set_data.get("sealedProduct"):
                print(f"Sealed Product for {set_code} not found, skipping")
                continue

            print(f"Building {set_code}")
            for sealed_product in set_data["sealedProduct"]:
                cards_map = self.get_cards_in_sealed_product(
                    set_code, sealed_product.get("uuid")
                )
                for card in cards_map.keys():
                    return_value[card].add(sealed_product.get("uuid"))

        return return_value

    def get_cards_in_sealed_product(
        self, set_code: str, sealed_product_uuid: str
    ) -> Dict[Card, Set[str]]:
        return_value = defaultdict(set)

        for sealed_product in self.mtgjson_data[set_code]["sealedProduct"]:
            if sealed_product_uuid != sealed_product.get("uuid"):
                continue

            for content_key, contents in sealed_product.get("contents", {}).items():
                for content in contents:
                    cards = self.get_cards_in_content_type(content_key, content)
                    for card in cards:
                        return_value[card].add(sealed_product_uuid)
            break

        return return_value

    @staticmethod
    def get_card_obj_from_card(card_content: Dict[str, Any]) -> List[Card]:
        finish = "foil" if card_content.get("foil") else "nonfoil"
        if "uuid" in card_content:
            return [Card(card_content["uuid"], finish)]
        else:
            return []

    def get_cards_in_content_type(
        self, content_key: str, content: Dict[str, Any]
    ) -> List[Card]:
        if content_key == "card":
            """
            "card": [
                {
                    "foil": true,
                    "name": "Elvish Champion",
                    "number": "241★",
                    "set": "8ed",
                    "uuid": "51729dab-95a0-59f0-a829-82dc2d748c1d"
                }
            ]
            """
            return self.get_card_obj_from_card(content)

        if content_key == "pack":
            """
            "pack": [
                {
                    "code": "default",
                    "set": "10e"
                }
            ]
            """
            return self.get_cards_in_pack(content["set"].upper(), content["code"])

        if content_key == "sealed":
            """
            "sealed": [
                {
                    "count": 36,
                    "name": "Tenth Edition Booster Pack",
                    "set": "10e",
                    "uuid": "c690e178-661d-5e17-9b29-a5bf6319a844"
                }
            ]
            """
            if "uuid" not in content:
                return []
            return self.get_cards_in_content_type(
                content["set"].upper(), content.get("uuid")
            )

        if content_key == "deck":
            """
            "deck": [
                {
                    "name": "Deck Name",
                    "set": "10e"
                }
            ]
            """
            return self.get_cards_in_deck(content["set"].upper(), content["name"])

        if content_key == "variable":
            """
            "variable": [
            {
                "configs": [
                    {
                        "deck": [
                            {
                                "name": "A Welcome Deck - White",
                                "set": "w17"
                            },
                            {
                                "name": "A Welcome Deck - Blue",
                                "set": "w17"
                            }
                        ]
                    }
                ]
            }
            """
            return_value = set()
            for config in content["configs"]:
                for deck in config.get("deck", []):
                    return_value.update(
                        self.get_cards_in_deck(deck["set"].upper(), deck["name"])
                    )
                for sealed in config.get("sealed", []):
                    return_value.update(
                        self.get_cards_in_sealed_product(
                            sealed["set"].upper(), sealed.get("uuid", None)
                        )
                    )
                for pack in config.get("pack", []):
                    return_value.update(
                        self.get_cards_in_pack(
                            pack["set"].upper(), pack["code"]
                        )
                    )
                for card in config.get("card", []):
                    return_value.update(self.get_card_obj_from_card(card))

            return list(return_value)

        return []

    def get_cards_in_pack(self, set_code: str, booster_code: str) -> List[Card]:
        try:
            booster_data = self.mtgjson_data[set_code].get("booster")
        except:
            return []
        if not booster_data:
            return []

        sheet_data = booster_data.get(booster_code)
        if not sheet_data:
            return []

        sheets_to_poll = set()
        for booster in sheet_data["boosters"]:
            sheets_to_poll.update(booster["contents"].keys())

        return_value = set()
        for sheet in sheets_to_poll:
            cards_in_sheet = sheet_data["sheets"][sheet]["cards"]

            for card_uuid in cards_in_sheet.keys():
                # Validate a card can effectively be etched or foil by looking
                # at the finish array. To retrieve this info we need to iterate
                # on the possible set codes present in the pack
                for code in sheet_data["sourceSetCodes"]:
                    for card in self.mtgjson_data[code]["cards"]:
                        if card_uuid == card["uuid"]:
                            finishes = card["finishes"]

                if ("etched" in sheet.lower() or sheet_data["sheets"][sheet]["foil"]) and "etched" in finishes:
                    finish = "etched"
                else:
                    finish = "foil" if sheet_data["sheets"][sheet]["foil"] and "foil" in finishes else "nonfoil"

                return_value.add(Card(card_uuid, finish))

        return list(return_value)

    def get_cards_in_deck(self, set_code: str, deck_name: str) -> List[Card]:
        try:
            decks_data = self.mtgjson_data[set_code].get("decks")
        except:
            return []
        if not decks_data:
            return []

        return_value = set()
        for deck in decks_data:
            if deck["name"] != deck_name:
                continue
            deck_cards = (
                deck.get("cards", [])
                + deck.get("mainBoard", [])
                + deck.get("sideBoard", [])
                + deck.get("displayCommander", [])
                + deck.get("commander", [])
                + deck.get("tokens", [])
                + deck.get("schemes", [])
                + deck.get("planes", [])
                + deck.get("planarDeck", [])
                + deck.get("schemeDeck", [])
            )
            for deck_card in deck_cards:
                finish = "nonfoil"
                # Validate a card can effectively be etched or foil by looking
                # at the finish array. To retrieve this info we need to iterate
                # on the possible set codes present in the deck
                for code in deck["sourceSetCodes"]:
                    for card in self.mtgjson_data[code]["cards"]:
                        if deck_card["uuid"] == card["uuid"]:
                            finishes = card["finishes"]

                if (deck_name.endswith("etched") or deck_card.get("isFoil", False)) and "etched" in finishes:
                    finish = "etched"
                elif deck_card.get("isFoil", False) and "foil" in finishes:
                    finish = "foil"
                return_value.add(Card(deck_card["uuid"], finish))
            break

        return list(return_value)


def results_to_json(
    build_data: Dict[Card, Set[str]]
) -> Dict[str, Dict[str, List[str]]]:
    return_value = defaultdict(lambda: defaultdict(list))
    for card, product_uuids in build_data.items():
        return_value[card.uuid][card.finish] = sorted(product_uuids)
    return return_value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("card2product")

    parser.add_argument("--output-file", "-o", type=str, required=True)
    parser.add_argument("--mtgjson", "-m", type=str, required=False)
    parser.add_argument("--set", "-s", type=str, required=False)

    return parser.parse_args()


def main(args: argparse.Namespace):
    card_to_products_data = MtgjsonCardLinker(args.mtgjson).build(args.set)
    with pathlib.Path(args.output_file).expanduser().open("w", encoding="utf-8") as fp:
        json.dump(results_to_json(card_to_products_data), fp, indent=4, sort_keys=True)


if __name__ == "__main__":
    main(parse_args())

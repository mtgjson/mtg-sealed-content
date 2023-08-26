import argparse
import json
import pathlib
from collections import defaultdict
from typing import Any, Dict, Set, List, Optional


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

    def __init__(self, all_printings_path: str):
        _all_printings_path = pathlib.Path(all_printings_path).expanduser()
        if not _all_printings_path.exists():
            raise FileNotFoundError

        with _all_printings_path.open(encoding="utf-8") as fp:
            self.mtgjson_data = json.load(fp).get("data")

    def build(self) -> Dict[Card, Set[str]]:
        return_value = defaultdict(set)

        for set_code, set_data in self.mtgjson_data.items():
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
        finish = "foil" if card_content.get("Foil") else "nonfoil"
        return [Card(card_content["uuid"], finish)]

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
            return self.get_cards_in_content_type(
                content["set"].upper(), content["uuid"]
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
                            sealed["set"].upper(), sealed["uuid"]
                        )
                    )
                for card in config.get("card", []):
                    return_value.update(self.get_card_obj_from_card(card))

            return list(return_value)

        return []

    def get_cards_in_pack(self, set_code: str, booster_code: str) -> List[Card]:
        booster_data = self.mtgjson_data[set_code].get("booster")
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

            if "etched" in sheet.lower():
                finish = "etched"
            else:
                finish = "foil" if sheet_data["sheets"][sheet]["foil"] else "nonfoil"

            for card_uuid in cards_in_sheet.keys():
                return_value.add(Card(card_uuid, finish))

        return list(return_value)

    def get_cards_in_deck(self, set_code: str, deck_name: str) -> List[Card]:
        decks_data = self.mtgjson_data[set_code].get("decks")
        if not decks_data:
            return []

        return_value = set()
        for deck in decks_data:
            if deck["name"] != deck_name:
                continue

            for card in deck["cards"]:
                return_value.add(Card(card["uuid"], card["finish"]))
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
    parser = argparse.ArgumentParser("mtgjson5")

    parser.add_argument("--input-file", "-i", type=str, required=True)
    parser.add_argument("--output-file", "-o", type=str, required=True)

    return parser.parse_args()


def main(args: argparse.Namespace):
    card_to_products_data = MtgjsonCardLinker(args.input_file).build()
    with pathlib.Path(args.output_file).expanduser().open("w", encoding="utf-8") as fp:
        json.dump(results_to_json(card_to_products_data), fp, indent=4, sort_keys=True)


if __name__ == "__main__":
    main(parse_args())

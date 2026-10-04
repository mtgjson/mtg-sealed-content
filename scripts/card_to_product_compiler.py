from mtg_sealed_choices.links import CardReference as Card, results_to_json
from mtg_sealed_choices.catalog import CatalogWalker
if __package__:
    from .atomic_write import atomic_write
else:
    from atomic_write import atomic_write

import argparse
import json
import lzma
import os
import pathlib
from collections import defaultdict
from typing import Any, Dict, Set
import requests


class MtgjsonCardLinker(CatalogWalker):
    mtgjson_data: Dict[str, Any]

    # We grab the .xz build (~92 MB vs ~622 MB raw) and decompress with stdlib
    # lzma. Try the live v5 feed first, then fall back to the v5_backup snapshot
    # if it's unreachable or missing the sealed/deck data this mapper needs (as
    # happened with the 5.3.0+20260731 build). Both are overridable via env.
    PRIMARY_URL = os.environ.get(
        "MTGJSON_ALLPRINTINGS_URL",
        "https://mtgjson.com/api/v5/AllPrintings.json.xz",
    )
    BACKUP_URL = os.environ.get(
        "MTGJSON_ALLPRINTINGS_BACKUP_URL",
        "https://mtgjson.com/api/v5_backup/AllPrintings.json.xz",
    )

    def __init__(self, mtgjson_path: str):
        if mtgjson_path:
            print("Loading local AllPrintings.json")
            with open(mtgjson_path) as f:
                self.mtgjson_data = json.load(f).get("data")
        else:
            self.mtgjson_data = self._download_mtgjson_data()

        if not self.mtgjson_data:
            raise RuntimeError("AllPrintings data is empty or missing 'data' key")

    def _download_mtgjson_data(self) -> Dict[str, Any]:
        try:
            data = self._fetch_all_printings(self.PRIMARY_URL)
            if self._has_required_data(data):
                return data
            print("Live AllPrintings is missing sealed/deck data, using backup")
        except requests.RequestException as exc:
            print(f"Failed to download live AllPrintings ({exc}), using backup")

        return self._fetch_all_printings(self.BACKUP_URL)

    @staticmethod
    def _fetch_all_printings(url: str) -> Dict[str, Any]:
        print(f"Downloading AllPrintings from {url}")
        request_wrapper = requests.get(url, timeout=(10, 60))
        request_wrapper.raise_for_status()

        content = request_wrapper.content
        if url.endswith(".xz"):
            content = lzma.decompress(content)

        return json.loads(content).get("data")

    @staticmethod
    def _has_required_data(data: Dict[str, Any]) -> bool:
        if not data:
            return False
        has_sealed = any(s.get("sealedProduct") for s in data.values())
        has_decks = any(s.get("decks") for s in data.values())
        return has_sealed and has_decks

    def build(self, code: str, debug: bool) -> Dict[Card, Set[str]]:
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
                print(f"Mapping {sealed_product.get('name')}")

                cards_list = self.get_cards_in_sealed_product(
                    set_code, sealed_product.get("uuid")
                )
                product = sealed_product.get("uuid")
                if debug:
                    product = sealed_product.get("name")
                for card in cards_list:
                    return_value[card].add(product)

        return return_value

    def extra_pack_finishes(self, source_code: str, card: dict) -> set[str]:
        # Preserve the legacy corrections; MTGJSON's pipeline has no such fallback.
        if source_code == "MH2" and not 262 <= int(card["number"]) <= 441:
            return set()
        return {"etched"} if source_code in {"H1R", "MH2", "STA"} else set()

    def missing_deck_source(self, code: str) -> None:
        print(f"Note: {code} was NOT found in mtgjson")

    def pack_source_cards(self, code: str) -> list[dict]:
        return self.mtgjson_data[code]["cards"]

    def deck_source_codes(self, deck: dict) -> list[str]:
        return deck["sourceSetCodes"]

    def sealed_products(self, code: str) -> list[dict]:
        return self.mtgjson_data[code]["sealedProduct"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("card2product")

    parser.add_argument("--output-file", "-o", type=str, required=False)
    parser.add_argument("--mtgjson", "-m", type=str, required=False)
    parser.add_argument("--set", "-s", type=str, required=False)
    parser.add_argument("--debug", "-d", type=bool, required=False)

    return parser.parse_args()


def main(args: argparse.Namespace):
    if not args.output_file:
        if args.set:
            args.output_file = args.set + ".json"
        else:
            raise RuntimeError("Missing output path")

    card_to_products_data = MtgjsonCardLinker(args.mtgjson).build(args.set, args.debug)

    if not card_to_products_data:
        print("Build produced no card-to-product mappings; skipping write to avoid clobbering existing output")
        return

    with atomic_write(pathlib.Path(args.output_file).expanduser(), encoding='utf-8') as fp:
        json.dump(results_to_json(card_to_products_data), fp, indent=4, sort_keys=True)


if __name__ == "__main__":
    main(parse_args())

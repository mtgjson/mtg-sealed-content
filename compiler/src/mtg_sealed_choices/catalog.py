"""Walk AllPrintings-shaped catalogs, with consumer-specific policy hooks."""

from __future__ import annotations

from typing import cast

from .links import CardReference, deck_cards, explicit_card, variable_cards


class CatalogWalker:
    def __init__(self, data: dict) -> None:
        self.mtgjson_data = data

    def missing_deck_source(self, code: str) -> None:
        """Report a deck source set missing from the supplied catalog."""

    def extra_pack_finishes(self, source_code: str, card: dict) -> set[str]:
        """Optional legacy finish corrections for a matched foil-sheet card."""
        return set()

    def product_language(self, product: dict) -> str | None:
        return None

    def deck_card_uuid(self, card: dict, language: str | None, set_code: str, deck_name: str) -> str:
        return cast(str, card["uuid"])

    def unknown_content(self, key: str) -> None:
        raise ValueError(f"Unknown content_key: {key}")

    def pack_source_cards(self, code: str) -> list[dict]:
        return cast(list[dict], self.mtgjson_data.get(code, {}).get("cards", []))

    def deck_source_codes(self, deck: dict) -> list[str]:
        return cast(list[str], deck.get("sourceSetCodes", []))

    def sealed_products(self, code: str) -> list[dict]:
        return cast(list[dict], self.mtgjson_data.get(code, {}).get("sealedProduct", []))

    get_card_obj_from_card = staticmethod(explicit_card)

    def get_cards_in_pack(self, set_code: str, booster_code: str) -> list[CardReference]:
        boosters = self.mtgjson_data.get(set_code, {}).get("booster") or {}
        config = boosters.get(booster_code)
        if not config:
            return []
        sheets = {sheet for booster in config["boosters"] for sheet in booster["contents"]}
        result: set[CardReference] = set()
        for name in sheets:
            sheet = config["sheets"][name]
            for uuid in sheet["cards"]:
                finish = "nonfoil"
                extra: set[str] = set()
                if sheet["foil"]:
                    finishes = []
                    for code in config["sourceSetCodes"]:
                        for card in self.pack_source_cards(code):
                            if card["uuid"] == uuid:
                                finishes = card["finishes"]
                                extra = self.extra_pack_finishes(code, card)
                    if ("etched" in name.lower() or len(finishes) == 1) and "etched" in finishes:
                        finish = "etched"
                    elif "foil" in finishes:
                        finish = "foil"
                result.add(CardReference(uuid, finish))
                result.update(CardReference(uuid, treatment) for treatment in extra)
        return list(result)

    def get_cards_in_deck(self, set_code: str, deck_name: str, language: str | None = None) -> list[CardReference]:
        result: set[CardReference] = set()
        for deck in self.mtgjson_data.get(set_code, {}).get("decks") or []:
            if deck["name"] != deck_name:
                continue
            for card in deck_cards(deck):
                finishes = []
                for code in self.deck_source_codes(deck):
                    if code not in self.mtgjson_data:
                        self.missing_deck_source(code)
                        continue
                    source = self.mtgjson_data[code]
                    for printing in source["cards"] + source["tokens"]:
                        if card["uuid"] == printing["uuid"]:
                            finishes = printing["finishes"]
                            break
                finish = "nonfoil"
                if card.get("isEtched", False) and "etched" in finishes:
                    finish = "etched"
                elif card.get("isFoil", False) and "foil" in finishes:
                    finish = "foil"
                result.add(CardReference(self.deck_card_uuid(card, language, set_code, deck_name), finish))
            break
        return list(result)

    def get_cards_in_sealed_product(self, set_code: str, uuid: str | None) -> list[CardReference]:
        result: set[CardReference] = set()
        for product in self.sealed_products(set_code):
            if product.get("uuid") != uuid:
                continue
            language = self.product_language(product)
            for kind, entries in product.get("contents", {}).items():
                # card_count and similar scalar metadata are not card entries.
                if isinstance(entries, list):
                    for entry in entries:
                        result.update(self.get_cards_in_content_type(kind, entry, language))
            break
        return list(result)

    def get_cards_in_content_type(self, key: str, content: dict, language: str | None = None) -> list[CardReference]:
        if key == "card":
            return explicit_card(content)
        if key == "pack":
            return self.get_cards_in_pack(content["set"].upper(), content["code"])
        if key == "deck":
            return self.get_cards_in_deck(content["set"].upper(), content["name"], language)
        if key == "sealed":
            # A nested product has its own language; never inherit its parent's.
            return self.get_cards_in_sealed_product(content["set"].upper(), content.get("uuid"))
        if key == "variable":
            return variable_cards(content, lambda kind, entry: self.get_cards_in_content_type(kind, entry, language))
        if key != "other":
            self.unknown_content(key)
        return []

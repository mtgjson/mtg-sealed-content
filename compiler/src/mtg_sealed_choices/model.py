"""Shared recipe objects; consumers supply catalog resolution and diagnostics."""

from __future__ import annotations

from typing import Any, ClassVar

from . import ChoiceGroups


class Card:
    def __init__(self, contents: dict) -> None:
        self.name: str = contents["name"]
        self.set: str = contents["set"]
        self.number: str | int = contents["number"]
        self.etched: bool = contents.get("etched", False)
        self.foil: bool = contents.get("foil", False)
        self.token: bool = contents.get("token", False)
        self.uuid: str | bool | None = contents.get("uuid", False)

    def toJson(self) -> dict:
        data: dict = {"name": self.name, "set": self.set, "number": str(self.number)}
        if self.uuid:
            data["uuid"] = self.uuid
        if self.foil:
            data["foil"] = self.foil
        if self.etched:
            data["etched"] = self.etched
        if self.token:
            data["token"] = self.token
        return data


class Pack:
    def __init__(self, contents: dict) -> None:
        self.set: str = contents["set"]
        self.code: str = contents["code"]

    def toJson(self) -> dict:
        return {"set": self.set, "code": self.code}


class Deck:
    def __init__(self, contents: dict) -> None:
        self.set: str = contents["set"]
        self.name: str = contents["name"]

    def toJson(self) -> dict:
        return {"set": self.set, "name": self.name}


class Sealed:
    def __init__(self, contents: dict) -> None:
        self.set: str = contents["set"]
        self.count: int = contents["count"]
        self.name: str = contents["name"]
        self.uuid: str | bool | None = contents.get("uuid", False)

    def toJson(self) -> dict:
        data: dict = {"set": self.set, "count": self.count, "name": self.name}
        if self.uuid:
            data["uuid"] = self.uuid
        return data


class Other:
    def __init__(self, contents: dict) -> None:
        self.name: str = contents["name"]

    def toJson(self) -> dict:
        return {"name": self.name}


class Product:
    """A recipe tree with independent variable groups and adapter-owned leaves."""

    card_type: ClassVar[type[Any]] = Card
    pack_type: ClassVar[type[Any]] = Pack
    deck_type: ClassVar[type[Any]] = Deck
    sealed_type: ClassVar[type[Any]] = Sealed
    other_type: ClassVar[type[Any]] = Other

    def __init__(self, contents: dict | None, set_code: str | None = None, name: str | None = None) -> None:
        self.name = name
        self.set_code = set_code
        self.uuid: str | None = None
        contents = contents or {}
        self.card = [self.card_type(c) for c in contents.get("card", [])]
        self.pack = [self.pack_type(p) for p in contents.get("pack", [])]
        self.deck = [self.deck_type(d) for d in contents.get("deck", [])]
        self.sealed = []
        for s in contents.get("sealed", []):
            if s["name"] == self.name:
                raise ValueError(f"Self-referrential product {self.name}")
            self.sealed.append(self.sealed_type(s))
        self.other = []
        for o in contents.get("other", []):
            self.other.append(self.other_type(o))
            if o["name"] == "Bonus card unknown":
                self.unknown_bonus()
        self.chance: int | float = contents.get("chance", 1)
        self.weight: int | float = contents.get("weight", 0)
        self.card_count: int = contents.get("card_count", 0)
        self.choices = ChoiceGroups(contents, type(self), self.name)

    def unknown_bonus(self) -> None:
        """Adapter hook for an incomplete bonus definition."""

    def resolve_uuid(self, uuid_map: dict) -> None:
        """Adapter hook for the enclosing product's catalog identifier."""

    def serialized_cards(self) -> list[dict]:
        """Adapters may omit unresolved entries required by their output schema."""
        return [c.toJson() for c in self.card]

    def merge(self, target: Product) -> None:
        for key in ("card", "pack", "deck", "sealed", "other"):
            getattr(self, key).extend(getattr(target, key))
        self.choices.merge(target.choices)
        self.card_count += target.card_count
        self.chance *= target.chance

    def toJson(self) -> dict:
        data: dict = {}
        cards = self.serialized_cards()
        if cards:
            data["card"] = cards
        for key in ("pack", "deck", "sealed", "other"):
            values = getattr(self, key)
            if values:
                data[key] = [value.toJson() for value in values]
        if self.choices.groups:
            data["variable"] = self.choices.serialize(lambda component: component.toJson())
        if self.card_count:
            data["card_count"] = self.card_count
        if self.weight:
            data["variable_config"] = [{"chance": self.chance, "weight": self.weight}]
        return data

    def get_uuids(self, uuid_map: dict) -> None:
        self.resolve_uuid(uuid_map)
        for key in ("card", "pack", "deck", "sealed"):
            for entry in getattr(self, key):
                entry.get_uuids(uuid_map)
        for group in self.choices.groups:
            for child in group:
                child.get_uuids(uuid_map)


def deck_links(all_products: dict) -> dict:
    """Map directly contained decks to the enclosing product UUIDs."""
    result: dict = {}
    for products in all_products.values():
        for product in products.values():
            if product.uuid:
                for deck in product.deck:
                    result.setdefault(deck.set, {}).setdefault(deck.name, []).append(product.uuid)
    return result

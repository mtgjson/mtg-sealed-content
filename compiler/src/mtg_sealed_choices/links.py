"""Catalog-independent card membership traversal and reverse-link output."""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")
CONTENT_TYPES = ("card", "pack", "sealed", "deck", "variable", "other")
DECK_BOARDS = (
    "cards",
    "mainBoard",
    "sideBoard",
    "displayCommander",
    "commander",
    "tokens",
    "schemes",
    "planes",
    "planarDeck",
    "schemeDeck",
)


@dataclass(frozen=True)
class CardReference:
    uuid: str
    finish: str


def explicit_card(content: dict) -> list[CardReference]:
    finish = "etched" if content.get("etched") else "foil" if content.get("foil") else "nonfoil"
    return [CardReference(content["uuid"], finish)] if "uuid" in content else []


def variable_cards(content: dict, resolve: Callable[[str, dict], Iterable[T]]) -> list[T]:
    """Visit every alternative, including nested groups, ignoring metadata.

    Membership is a union, not a probability calculation. The callback keeps
    catalog lookup, language context, and finish policy in the consumer.
    """
    result: set[T] = set()
    for config in content["configs"]:
        for kind in CONTENT_TYPES:
            for entry in config.get(kind, []):
                result.update(resolve(kind, entry))
    return list(result)


def deck_cards(deck: dict) -> list[dict]:
    return [card for board in DECK_BOARDS for card in deck.get(board, [])]


def results_to_json(build_data: dict[CardReference, set[str]]) -> dict[str, dict[str, list[str]]]:
    result: dict[str, dict[str, list[str]]] = {}
    for card, products in build_data.items():
        result.setdefault(card.uuid, {})[card.finish] = sorted(products)
    return result

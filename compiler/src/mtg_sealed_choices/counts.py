"""How many cards a deck or a booster holds, read from the catalog."""

from __future__ import annotations

from collections import Counter


def _sections(deck: dict) -> tuple[list[list[dict]], list[dict]]:
    """A deck's playable sections and its tokens, in source or compiled JSON.

    Source JSON keeps tokens inline, flagged, and display commanders in a
    section of their own; compiled JSON keeps both apart from the main deck.
    """
    cards = deck["cards"]
    if isinstance(cards, dict):
        sections = [section for name, section in cards.items() if name != "Display Commander"]
        tokens = [card for section in sections for card in section if card.get("token", False)]
        return sections, tokens
    sections = [cards] + [deck.get(name, []) for name in ("commander", "sideboard", "planarDeck", "schemeDeck")]
    return sections, deck.get("tokens", [])


def playable_cards(deck: dict) -> list[dict]:
    """A deck's cards, display commanders and tokens left out."""
    sections, _ = _sections(deck)
    return [card for section in sections for card in section if not card.get("token", False)]


def deck_card_count(deck: dict) -> int:
    """How many cards a deck holds: its playable cards, or its tokens where
    it holds nothing else, as an Enemy Deck of token-typed cards does."""
    count = sum(card["count"] for card in playable_cards(deck))
    if count:
        return count
    _, tokens = _sections(deck)
    return sum(card["count"] for card in tokens)


def deck_is_all_foil(deck: dict) -> bool:
    """Whether a deck has playable cards and every one of them is foil."""
    cards = playable_cards(deck)
    return bool(cards) and all(card.get("foil") or card.get("etched") for card in cards)


def booster_card_count(config: dict) -> int | None:
    """How many cards a booster holds: the size most of its weight opens to,
    the larger on a tie, or None for a booster with no weight to read."""
    sizes: Counter[int] = Counter()
    for booster in config.get("boosters", []):
        sizes[sum(booster["contents"].values())] += booster.get("weight", 0)
    if not sizes:
        return None
    return max(sizes, key=lambda size: (sizes[size], size))

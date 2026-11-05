def playable_cards(deck):
    """A deck's playable cards in either source or compiled deck JSON."""
    cards = deck["cards"]
    if isinstance(cards, dict):
        # Source JSON keeps tokens inline and display commanders in a section.
        sections = [
            section for name, section in cards.items()
            if name != "Display Commander"
        ]
    else:
        # Compiled JSON separates these from the main deck. Tokens and display
        # commanders are accessories and do not contribute to card_count.
        sections = [cards] + [
            deck.get(name, [])
            for name in ("commander", "sideboard", "planarDeck", "schemeDeck")
        ]
    return [
        card
        for section in sections
        for card in section
        if not card.get("token", False)
    ]


def deck_card_count(deck):
    """Count playable deck contents in either source or compiled deck JSON."""
    return sum(card["count"] for card in playable_cards(deck))


def deck_is_all_foil(deck):
    """Whether a deck has playable cards and every one of them is foil."""
    cards = playable_cards(deck)
    return bool(cards) and all(card.get("foil") or card.get("etched") for card in cards)

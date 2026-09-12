def deck_card_count(deck):
    """Count playable deck contents in either source or compiled deck JSON."""
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
    return sum(
        card["count"]
        for section in sections
        for card in section
        if not card.get("token", False)
    )

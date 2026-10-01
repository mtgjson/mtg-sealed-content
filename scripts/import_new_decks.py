if __package__:
    from . import sealed_yaml
else:
    import sealed_yaml

import json
import os
import sys
from pathlib import Path
import requests
if __package__:
    from .deck_card_count import deck_card_count
else:
    from deck_card_count import deck_card_count


def load_referenced_decks():
    """Collect every (set, deck_name) already referenced by a `deck` entry in
    any product's contents.

    This is a live scan of the source files. It replaces an earlier check against
    outputs/deck_map.json, which is a compiled snapshot that can lag behind
    manually-added products: a deck already modeled under a hand-authored product
    name (e.g. "... Welcome Deck Black" referencing the "Black Deck" decklist)
    would then get a second stub product created for it ("... Welcome Deck Black
    Deck") on the next run.
    """
    referenced = set()
    for _, data in sealed_yaml.iter_sets():
        for product in data["products"].values():
            for entry in (product.get("contents") or {}).get("deck", []) or []:
                if isinstance(entry, dict) and entry.get("name"):
                    referenced.add((entry.get("set"), entry["name"]))
    return referenced


def load_decks():
    # Prefer a locally-built decklist JSON when one is supplied via $DECKS_JSON. The
    # daily workflow builds it straight from the magic-preconstructed-decks source
    # (its own bin/build_jsons), so a decklist added today is picked up today rather
    # than waiting for the separately-scheduled magic-preconstructed-decks-data
    # export. Fall back to the compiled snapshot when run by hand.
    local_decks = os.environ.get("DECKS_JSON")
    if local_decks and Path(local_decks).exists():
        with open(local_decks) as f:
            decks = json.load(f)
        print(f"Loaded {len(decks)} decks from local build {local_decks}")
    else:
        gh_request = requests.get(
            "https://raw.githubusercontent.com/taw/magic-preconstructed-decks-data/refs/heads/master/decks_v2.json",
            timeout=(10, 60),
        )
        gh_request.raise_for_status()

        try:
            decks = json.loads(gh_request.content)
        except json.JSONDecodeError:
            print("unable to load magic-preconstructed-decks-data file, here are the contents")
            print(gh_request.content)
            sys.exit(1)
    return decks


skip_types = [
    # skip mtgo decks
    "Arena",
    "Historic Brawl",
    "MTGO Commander",
    "MTGO Duel",
    "MTGO Theme",
    "Shandalar",
    # skip artificial decks
    "Bundle Land Pack",
    # referenced manually from contents; the products already exist under
    # names that don't follow this script's naming convention
    "Challenge Deck",
    # skip randomized decks
    "Clash Pack",
    "Sample Deck",
    "Toolkit",
    "Jumpstart",
    # not supported downstream
    "Enhanced Deck",
    "Advanced Deck",
]

skip_sets = [
    # The decks found in this set are not associated to any product
    "pvan",
    # The SDCC promos are duplicated and already loaded
    "psdc", "ps14", "ps15", "ps16", "ps17", "ps18", "ps19",
    # More online-only sets
    "td0", "td2",
]

skip_names = [
    # Randomized decks
    "Battle Pack",
]


category_fixups = {
    "BOX": "BOX_SET",
}

subtype_fixups = {
    "BOX_SET": "OTHER",
    "BRAWL_DECK": "BRAWL",
    "COMMANDER_DECK": "COMMANDER",
    "THEME_DECK": "THEME",
    "WELCOME_DECK": "WELCOME",
}


def add_product(set_code, name, deck):
    stem = set_code.upper()
    if sealed_yaml.set_exists(stem):
        data = sealed_yaml.load_set(stem)
    else:
        data = sealed_yaml.new_set(set_code)

    # Merge into any existing entry instead of replacing it, so identifiers,
    # language and researched contents survive the import
    product = data["products"].setdefault(name, {})
    product.setdefault("identifiers", {})

    category = deck["category"].upper().replace(" ", "_")
    subtype = deck["type"].upper().replace(" ", "_")

    if category in category_fixups:
        category = category_fixups[category]

    # Override fields for specific sets
    if set_code in ["sld", "slc"]:
        category = "BOX_SET"
        subtype = "SECRET_LAIR"

    # Fixup subtypes
    # XXX maybe we should propagate these types from upstream instead of having our own?
    if subtype in subtype_fixups:
        subtype = subtype_fixups[subtype]

    if name.endswith("Draft Night Case"):
        category = "LIMITED_CASE"
        subtype = "DRAFT"
    elif name.endswith("Draft Night"):
        category = "LIMITED"
        subtype = "DRAFT"

    product["category"] = category
    product["subtype"] = subtype
    product["release_date"] = deck["release_date"]

    # setdefault only fills fields that aren't already present, so an existing
    # entry keeps whatever has been researched for it
    content = product.setdefault("contents", {})
    content.setdefault("card_count", deck_card_count(deck))
    content.setdefault("deck", [{
        "name": deck["name"],
        "set": set_code,
    }])

    # we need to add a bonus card entry if no card has been set and there
    # isn't any other note (i.e. to mention that the drop has no bonus card
    if set_code == "sld" and ("card" not in content and "other" not in content):
        content.setdefault("other", [{
            "name": "Bonus card unknown",
        }])

    sealed_yaml.save_set(stem, data)


def main():
    referenced_decks = load_referenced_decks()
    decks = load_decks()
    for deck in decks:
        if any(tag in deck["type"] for tag in skip_types):
            continue
        if any(tag in deck["set_code"] for tag in skip_sets):
            continue
        if any(tag in deck["name"] for tag in skip_names):
            continue

        set_code = deck["set_code"]

        # If this decklist is already referenced by an existing contents entry, it is
        # already modeled (often under a hand-authored product name) -- don't create a
        # duplicate stub product for it.
        if (set_code, deck["name"]) in referenced_decks:
            print(f"Skipping {deck['name']} in {set_code}: deck already referenced in contents")
            continue

        print(f"Adding {deck['name']} to {set_code}")

        name = f"{deck['set_name']} {deck['type']} {deck['name']}"
        if set_code in ["sld", "slc"]:
            name = f"{deck['set_name']} {deck['name']}"
            # TODO: we should really follow upstream instead of tweaking the name
            name = name.replace(" Edition", "").replace("'", "").replace(":","").replace("-", " ")

        # Avoid duplicating the Commander tag from edition name and deck type above
        name = name.replace("Commander Commander", "Commander")

        add_product(set_code, name, deck)


if __name__ == "__main__":
    main()

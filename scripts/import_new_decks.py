import json
import os
import sys
from pathlib import Path
import requests
import yaml


def load_referenced_decks():
    """Collect every (set, deck_name) already referenced by a `deck` entry in
    any data/contents/*.yaml.

    This is a live scan of the source files. It replaces an earlier check against
    outputs/deck_map.json, which is a compiled snapshot that can lag behind
    manually-added products: a deck already modeled under a hand-authored product
    name (e.g. "... Welcome Deck Black" referencing the "Black Deck" decklist)
    would then get a second stub product created for it ("... Welcome Deck Black
    Deck") on the next run.
    """
    referenced = set()
    for path in Path("data/contents").glob("*.yaml"):
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        for product in (data.get("products") or {}).values():
            if not isinstance(product, dict):
                continue
            for entry in product.get("deck", []) or []:
                if isinstance(entry, dict) and entry.get("name"):
                    referenced.add((entry.get("set"), entry["name"]))
    return referenced


referenced_decks = load_referenced_decks()

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
    gh_request = requests.get("https://raw.githubusercontent.com/taw/magic-preconstructed-decks-data/refs/heads/master/decks_v2.json")

    try:
        decks = json.loads(gh_request.content)
    except json.JSONDecodeError:
        print("unable to load magic-preconstructed-decks-data file, here are the contents")
        print(gh_request.content)
        sys.exit(1)

# bin/build_jsons (v1) emits `cards` as a sections dict ({"Main Deck": [...]});
# the compiled decks_v2.json emits a flat list. Flatten so the card_count sum
# below works with either source.
for deck in decks:
    cards = deck.get("cards")
    if isinstance(cards, dict):
        deck["cards"] = [card for section in cards.values() for card in section]

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
    products_path = Path(f"data/products/{set_code.upper()}.yaml")

    # Create if non-existing
    if not products_path.exists():
        new_file = {
            "code": set_code,
            "products": {},
        }
        with open(products_path, "w") as f:
            yaml.safe_dump(new_file, f)

    # Load existing products and add the new one
    with open(products_path, "r") as f:
        products = yaml.safe_load(f)

        # Prepare new product definition -- if a previous identifiers is present preserve it
        new_product = {}
        new_product["category"] = deck["category"].upper().replace(" ", "_")
        new_product["identifiers"] = products["products"].get(name, {}).get("identifiers", {})
        new_product["subtype"] = deck["type"].upper().replace(" ", "_")
        new_product["release_date"] = deck["release_date"]

        if new_product["category"] in category_fixups:
            new_product["category"] = category_fixups[new_product["category"]]

        # Override fields for specific sets
        if set_code in ["sld", "slc"]:
            new_product["category"] = "BOX_SET"
            new_product["subtype"] = "SECRET_LAIR"

        # Fixup subtypes
        # XXX maybe we should propagate these types from upstream instead of having our own?
        if new_product["subtype"] in subtype_fixups:
            new_product["subtype"] = subtype_fixups[new_product["subtype"]]

        if name.endswith("Draft Night Case"):
            new_product["category"] = "LIMITED_CASE"
            new_product["subtype"] = "DRAFT"
        elif name.endswith("Draft Night"):
            new_product["category"] = "LIMITED"
            new_product["subtype"] = "DRAFT"

        products["products"][name] = new_product

    # Update file
    with open(products_path, "w") as f:
        yaml.safe_dump(products, f)


def add_content(set_code, name, deck):
    contents_path = Path(f"data/contents/{set_code.upper()}.yaml")

    if not contents_path.exists():
        new_file = {
            "code": set_code,
            "products": {},
        }
        with open(contents_path, "w") as f:
            yaml.safe_dump(new_file, f)

    with open(contents_path, "r") as f:
        contents = yaml.safe_load(f)

        # use setdefault to write fields that aren't already present in the
        # existing entry and create new ones if we're adding a new product.
        # Existing entries may be empty-list placeholders (e.g. `name: []`) —
        # treat those as empty dicts so setdefault works.
        content = contents["products"].get(name, {})
        if not isinstance(content, dict):
            content = {}

        card_count = sum(card["count"] for card in deck["cards"])
        content.setdefault("card_count", card_count)

        new_deck = [{
            "name": deck["name"],
            "set": set_code,
        }]
        content.setdefault("deck", new_deck)

        # we need to add a bonus card entry if no card has been set and there
        # isn't any other note (i.e. to mention that the drop has no bonus card
        if set_code == "sld" and ("card" not in content and "other" not in content):
            note = [{
                "name": "Bonus card unknown",
            }]
            content.setdefault("other", note)

        contents["products"][name] = content

    with open(contents_path, "w") as f:
        yaml.safe_dump(contents, f)


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
    add_content(set_code, name, deck)

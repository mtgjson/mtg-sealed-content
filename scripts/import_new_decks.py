import json
import sys
from pathlib import Path
import requests
import yaml


with open("outputs/deck_map.json", "rb") as f:
    current_decks = json.load(f)

gh_request = requests.get("https://raw.githubusercontent.com/taw/magic-preconstructed-decks-data/refs/heads/master/decks_v2.json")

try:
    decks = json.loads(gh_request.content)
except json.JSONDecodeError:
    print("unable to load magic-preconstructed-decks-data file, here are the contents")
    print(gh_request.content)
    sys.exit(1)

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

        # Override fields for specific sets
        if set_code in ["sld", "slc"]:
            new_product["category"] = "BOX_SET"
            new_product["subtype"] = "SECRET_LAIR"

        # Fixup a type
        if new_product["subtype"] == "THEME_DECK":
            new_product["subtype"] = "THEME"

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
        # existing entry and create new ones if we're adding a new product
        content = contents["products"].get(name, {})

        card_count = sum(card["count"] for card in deck["cards"])
        content.setdefault("card_count", card_count)

        new_deck = [{
            "name": deck["name"],
            "set": set_code,
        }]
        content.setdefault("deck", new_deck)

        # we need to add a bonus card entry if no card has been set and there
        # isn't any other note (i.e. to mention that the drop has no bonus card
        if set_code == "sld" and ("card" not in content and "other" not in existing_content):
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

    is_present = False
    for current_deck in current_decks.get(set_code, []):
        if current_deck == deck["name"]:
            is_present = True
            break

    if is_present:
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

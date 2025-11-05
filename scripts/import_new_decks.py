import json
from pathlib import Path
import requests
import yaml


with open("outputs/deck_map.json", "rb") as f:
    current_decks = json.load(f)

gh_request = requests.get("https://github.com/taw/magic-preconstructed-decks-data/blob/master/decks_v2.json?raw=true")
decks = json.loads(gh_request.content)

for deck in decks:
    set_code = deck["set_code"]

    skip_types = [
        # skip mtgo decks
        "Arena",
        "Historic Brawl",
        "MTGO Commander",
        "MTGO Duel",
        "MTGO Theme",
        "Shandalar",
        # skip randomized decks
        "Clash Pack",
        "Sample Deck",
        "Toolkit",
        "Jumpstart",
        # not supported downstream
        "Enhanced Deck",
        "Advanced Deck",
    ]
    if any(tag in deck["type"] for tag in skip_types):
        continue
    skip_sets = [
        # The decks found in this set are not associated to any product
        "pvan",
        # The SDCC promos are duplicated and already loaded
        "psdc", "ps14", "ps15", "ps16", "ps17", "ps18", "ps19",
        # More online-only sets
        "td0", "td2",
    ]
    if any(tag in set_code for tag in skip_sets):
        continue
    # Randomized decks
    if "Battle Pack" in deck["name"]:
        continue

    is_present = False
    for current_deck in current_decks.get(set_code, ""):
        if current_deck == deck["name"]:
            is_present = True
            break

    if not is_present:
        print(f"Adding {deck['name']} to {set_code}")

        name = f"{deck['set_name']} {deck['type']} {deck['name']}"
        if set_code == "sld":
            name = f"{deck['set_name']} {deck['name']}"
            # TODO: we should really follow upstream instead of tweaking the name
            name = name.replace(" Edition", "").replace("'", "").replace(":","").replace("-", " ")

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
        with open(products_path, "rb") as f:
            products = yaml.safe_load(f)

            # Prepare new product (load any existing data)
            new_product = products["products"].get(name, {})
            new_product["category"] = deck["category"].upper().replace(" ", "_")
            new_product["identifiers"] = {}
            new_product["subtype"] = deck["type"].upper().replace(" ", "_")
            new_product["release_date"] = deck["release_date"]

            products["products"][name] = new_product
        # Update file
        with open(products_path, "w") as f:
            yaml.safe_dump(products, f)

        # Same for new content
        contents_path = Path(f"data/contents/{set_code.upper()}.yaml")

        if not contents_path.exists():
            new_file = {
                "code": set_code,
                "products": {},
            }
            with open(contents_path, "w") as f:
                yaml.safe_dump(new_file, f)

        with open(contents_path, "rb") as f:
            contents = yaml.safe_load(f)
            new_content = contents["products"].get(name)
            if not isinstance(new_content, dict):
                new_content = {}

            new_content["card_count"] = len(deck["cards"])
            new_content["deck"] = [{
                "name": deck["name"],
                "set": set_code,
            }]

            # if it's a new SLD deck we need to add a bonus card entry
            if set_code == "sld":
                new_content["other"] = [{
                    "name": "Bonus card unknown",
                }]

            products["products"][name] = new_content

        with open(contents_path, "w") as f:
            yaml.safe_dump(contents, f)

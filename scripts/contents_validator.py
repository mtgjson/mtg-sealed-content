"""Validate sealed-product YAML, and (with --status) rebuild status.txt + deck_map.json.

This absorbs the status-report and deck-map role of product_contents_compiler.py so
that compiler can be retired:

  * status.txt      -- the per-product coverage report contributors rely on
  * deck_map.json   -- consumed by import_new_decks.py on the next run

The old compiler also emitted outputs/contents.json, but MTGJSON's own pipeline
(mtgjson5/pipeline/stages/sealed.py) now compiles the sealed contents directly from
this repo's raw YAML, so that output is unconsumed and is no longer produced here.

    python scripts/contents_validator.py            # fast structural validation (CI PR gate)
    python scripts/contents_validator.py --status   # also rebuild status.txt + deck_map.json
"""
import argparse
import json
import yaml
import product_classes as pc
from pathlib import Path

def build_uuid_map(mtgjson_path):
    import ijson
    import requests
    print("🤖 loading mtgjson...")
    try:
        if mtgjson_path:
            print("⚙️  using local AllPrintings.json")
            f = open(mtgjson_path, 'rb')
            parser = ijson.parse(f)
        else:
            print("⚙️  donwloading AllPrintings.json")
            url = "https://mtgjson.com/api/v5/AllPrintings.json"
            r = requests.get(url, stream=True)
            parser = ijson.parse(r.content)
    except:
        print("Could not load AllPrintings")
        return

    print("🤖 filtering sealed products...")

    uuids = {}
    current_set = ""
    status = ""
    name = ""
    number = ""
    uuid = ""
    holding = ""
    for prefix, event, value in parser:
        if prefix == "data" and event == "map_key":
            current_set = value
            ccode = current_set.lower()
            uuids[ccode] = {
                "booster": set(),
                "decks": set(),
                "sealedProduct": {},
                "cards": {},
            }
            status = ""
        elif prefix == f"data.{current_set}" and event == "map_key":
            status = value
        elif (
            status == "booster"
            and prefix == f"data.{current_set}.booster"
            and event == "map_key"
        ):
            uuids[ccode]["booster"].add(value)
        elif status == "decks" and prefix == f"data.{current_set}.decks.item.name":
            uuids[ccode]["decks"].add(value)
        elif status == "sealedProduct":
            if (
                prefix == f"data.{current_set}.sealedProduct.item"
                and event == "start_map"
            ):
                name = ""
                uuid = ""
            elif prefix == f"data.{current_set}.sealedProduct.item.name":
                name = value
            elif prefix == f"data.{current_set}.sealedProduct.item.uuid":
                uuid = value
            elif (
                prefix == f"data.{current_set}.sealedProduct.item"
                and event == "end_map"
            ):
                uuids[ccode]["sealedProduct"][name] = uuid
        elif status == "cards":
            # Only preserve the "main" face of the card
            if prefix == f"data.{current_set}.cards.item.side":
                if value != "a":
                    holding = "skip"
            if prefix == f"data.{current_set}.cards.item" and event == "start_map":
                number = ""
                name = ""
                uuid = ""
            elif prefix == f"data.{current_set}.cards.item.number":
                number = value
            elif prefix == f"data.{current_set}.cards.item.name":
                name = value
            elif prefix == f"data.{current_set}.cards.item.uuid":
                uuid = value
            elif prefix == f"data.{current_set}.cards.item" and event == "end_map":
                if holding != "skip":
                    uuids[ccode]["cards"][number] = (uuid, name)
                holding = ""

    if mtgjson_path:
        f.close()

    return uuids

def deck_links(all_products):
    deck_mapper = {}
    for set_contents in all_products.values():
        for product_contents in set_contents.values():
            if not product_contents.uuid:
                continue
            for deck in product_contents.deck:
                if deck.set not in deck_mapper:
                    deck_mapper[deck.set] = {}
                if deck.name not in deck_mapper[deck.set]:
                    deck_mapper[deck.set][deck.name] = []
                deck_mapper[deck.set][deck.name].append(product_contents.uuid)
    return deck_mapper

valid_categories = [
    "BOOSTER_PACK", "BOOSTER_BOX", "BOOSTER_CASE", "DECK", "MULTI_DECK",
    "DECK_BOX", "BOX_SET", "KIT", "BUNDLE", "BUNDLE_CASE",
    "LIMITED", "LIMITED_CASE", "SUBSET"
]

valid_subtypes = [
    "DEFAULT", "SET", "COLLECTOR", "JUMPSTART", "PROMOTIONAL", "THEME", "TOURNAMENT",
    "WELCOME", "TOPPER", "PLANESWALKER", "CHALLENGE", "EVENT", "CHAMPIONSHIP",
    "INTRO", "COMMANDER", "BRAWL", "ARCHENEMY", "PLANECHASE", "STARTER", "DRAFT_SET",
    "TWO_PLAYER_STARTER", "DUEL", "CLASH", "BATTLE", "GAME_NIGHT", "FROM_THE_VAULT",
    "SPELLBOOK", "SECRET_LAIR", "SECRET_LAIR_BUNDLE", "COMMANDER_COLLECTION",
    "COLLECTORS_EDITION", "GUILD_KIT", "DECK_BUILDERS_TOOLKIT", "LAND_STATION",
    "GIFT_BUNDLE", "FAT_PACK", "MINIMAL", "PREMIUM", "ADVANCED", "DRAFT", "PLAY",
    "SEALED_SET", "PRERELEASE", "OTHER", "CHALLENGER", "SIX", "CONVENTION", "REDEMPTION",
]

def validate_structure():
    contentFolder = Path("data/contents/")
    failed = False
    for set_file in contentFolder.glob("*.yaml"):
        with open(set_file, "rb") as f:
            contents = yaml.safe_load(f)

        for name, p in contents["products"].items():
            if not p:
                p = {}
            if isinstance(p, list):
                print(f"Product {name} in set {set_file.stem} formatted incorrectly")
                failed = True
                continue
            if set(p.keys()) == {"copy"}:
                p = contents["products"][p["copy"]]
            try:
                pc.product(p, contents["code"], name)
            except:
                print(f"Product {name} in set {set_file.stem} failed")
                failed = True
    if failed:
        raise ImportError()

    productsFolder = Path("data/products/")
    failed = False
    all_files = sorted(list(productsFolder.glob("*.yaml")))
    for set_file in all_files:
        with open(set_file, "rb") as f:
            contents = yaml.safe_load(f)

        for name, p in contents["products"].items():
            if "category" not in p.keys():
                print(f"Product {name} in set {set_file.stem} missing category")
                failed = True
            elif p['category'] not in valid_categories:
                if p['category'] == "UNKNOWN":
                    print(f"Product {name} missing a valid category")
                    #pass
                else:
                    print(f"Product {name} has an invalid category: {p['category']}")
                    failed = True
            if "subtype" not in p.keys():
                print(f"Product {name} in set {set_file.stem} missing subtype")
                failed = True
            elif p['subtype'] not in valid_subtypes:
                if p['subtype'] == "UNKNOWN":
                    print(f"Product {name} missing a valid subtype")
                    #pass
                else:
                    print(f"Product {name} uses an invalid subtype: {p['subtype']}")
                    failed = True
    if failed:
        raise ImportError()
    print("All products validated")

def rebuild_status_and_deck_map(uuid_map):
    """Rebuild status.txt (coverage) and outputs/deck_map.json.

    Same product compilation the old product_contents_compiler.py ran -- product
    construction and get_uuids() append the "missing contents" / "not found"
    lines to status.txt -- but without emitting the unconsumed contents.json."""
    products_contents = {}
    status_file = Path("status.txt")
    with open(status_file, "w") as f:
        f.write("Starting output\n")

    for set_file in sorted(Path("data/contents/").glob("*.yaml")):
        with open(set_file, "rb") as f:
            contents = yaml.safe_load(f)

        products_contents[contents["code"]] = {}
        for name, p in contents["products"].items():
            if not p:
                with open(status_file, "a") as f:
                    f.write(f"Product {contents['code']} - {name} missing contents\n")
                continue
            if set(p.keys()) == {"copy"}:
                p = contents["products"][p["copy"]]
            compiled_product = pc.product(p, contents["code"], name)
            compiled_product.get_uuids(uuid_map)
            products_contents[contents["code"]][name] = compiled_product
        if not products_contents[contents["code"]]:
            products_contents.pop(contents["code"])

    deck_map = deck_links(products_contents)
    with open("outputs/deck_map.json", "w") as outfile:
        json.dump(deck_map, outfile)

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser("contents_validator")
    parser.add_argument(
        "--status", action="store_true",
        help="rebuild status.txt + deck_map.json (loads MTGJSON AllPrintings)",
    )
    parser.add_argument(
        "--mtgjson", "-m", type=str, required=False,
        help="path to a local AllPrintings.json (downloaded if omitted)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.status:
        uuid_map = build_uuid_map(args.mtgjson)
        rebuild_status_and_deck_map(uuid_map)
        print("🤖 status.txt and deck_map.json written")
    else:
        validate_structure()

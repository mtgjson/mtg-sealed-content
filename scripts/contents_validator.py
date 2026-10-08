"""Validate sealed-product YAML, and (with --status) rebuild status.txt + deck_map.json.

This absorbs the status-report and deck-map role of product_contents_compiler.py so
that compiler can be retired:

  * status.txt      -- the per-product coverage report contributors rely on
  * deck_map.json   -- deck-to-product UUID mapping

The old compiler also emitted outputs/contents.json, but MTGJSON's own pipeline
(mtgjson5/pipeline/stages/sealed.py) now compiles the sealed contents directly from
this repo's raw YAML, so that output is unconsumed and is no longer produced here.

    python scripts/contents_validator.py            # fast structural validation (CI PR gate)
    python scripts/contents_validator.py --status   # validate, then rebuild status.txt + deck_map.json

--status validates first so that the push-to-main and scheduled workflows, which only
run --status, also refuse data that fails the PR gate.
"""
if __package__:
    from .atomic_write import atomic_write
    from . import sealed_yaml
else:
    from atomic_write import atomic_write
    import sealed_yaml

from mtg_sealed_choices.model import deck_links
from mtg_sealed_choices.uuid_map import uuid_map_from_events

import argparse
import copy
import json
import product_classes as pc
from pathlib import Path

if __package__:
    from .reference_validator import validate_references
else:
    from reference_validator import validate_references

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
            print("⚙️  downloading AllPrintings.json")
            url = "https://mtgjson.com/api/v5/AllPrintings.json"
            r = requests.get(url, stream=True, timeout=(10, 60))
            r.raise_for_status()
            parser = ijson.parse(r.content)
    except:
        print("Could not load AllPrintings")
        return

    print("🤖 filtering sealed products...")

    try:
        uuids = uuid_map_from_events(parser)
    finally:
        if mtgjson_path:
            f.close()

    return uuids


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
    "SEALED_SET", "PRERELEASE", "OTHER", "CHALLENGER", "SIX", "CONVENTION", "MTGO_REDEMPTION",
]

CONTENT_FIELDS = {
    "card": {"name", "set", "number", "foil", "etched", "token", "language", "uuid", "count"},
    "pack": {"set", "code"},
    "deck": {"set", "name"},
    "sealed": {"set", "name", "count", "uuid"},
    "other": {"name"},
}


def check_fields(value, allowed, path):
    if not isinstance(value, dict):
        raise ValueError(f"{path} must be a mapping")
    unknown = value.keys() - allowed
    if unknown:
        raise ValueError(f"{path}: unknown fields {sorted(unknown)}")


def check_count(value, path, minimum=1):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{path} must be an integer >= {minimum}")


def validate_content_fields(contents, path="contents"):
    # Empty entries are intentional placeholders for unresearched products.
    if contents is None or contents == []:
        return
    check_fields(contents, set(CONTENT_FIELDS) | {
        "variable", "variable_mode", "card_count", "chance", "weight"
    }, path)
    for key in ("card_count", "chance", "weight"):
        if key in contents:
            check_count(contents[key], f"{path}.{key}", minimum=0)
    for kind, fields in CONTENT_FIELDS.items():
        entries = contents.get(kind, [])
        if not isinstance(entries, list):
            raise ValueError(f"{path}.{kind} must be a list")
        for index, entry in enumerate(entries):
            entry_path = f"{path}.{kind}[{index}]"
            check_fields(entry, fields, entry_path)
            if "count" in entry:
                check_count(entry["count"], f"{entry_path}.count")
    if "variable" in contents:
        if not isinstance(contents["variable"], list):
            raise ValueError(f"{path}.variable must be a list")
        for index, entry in enumerate(contents["variable"]):
            validate_content_fields(entry, f"{path}.variable[{index}]")
    if "variable_mode" in contents:
        mode = contents["variable_mode"]
        check_fields(mode, {"count", "replacement", "weight"}, f"{path}.variable_mode")
        if "variable" not in contents:
            raise ValueError(f"{path}.variable_mode requires variable")
        for key in ("count", "weight"):
            if key in mode:
                check_count(mode[key], f"{path}.variable_mode.{key}")
        if "replacement" in mode and type(mode["replacement"]) is not bool:
            raise ValueError(f"{path}.variable_mode.replacement must be a boolean")


def validate_structure():
    failed = False
    for error in sealed_yaml.layout_errors():
        print(error)
        failed = True
    if failed:
        raise ImportError()

    sets = list(sealed_yaml.iter_sets())
    for stem, data in sets:
        products = data["products"]
        for name, entry in products.items():
            p = entry.get("contents")
            try:
                if isinstance(p, dict) and set(p) == {"copy"}:
                    p = products[p["copy"]].get("contents")
                validate_content_fields(p)
                # product() consumes variable_mode, so keep the loaded data intact
                pc.product(copy.deepcopy(p), data["code"], name)
            except (KeyError, TypeError, ValueError, AttributeError) as exc:
                print(f"Product {name} in set {stem} failed: {exc}")
                failed = True
    if failed:
        raise ImportError()

    split = sealed_yaml.is_split()
    for stem, data in sets:
        for name, p in data["products"].items():
            for key in sorted(set(p) - sealed_yaml.PRODUCT_KEYS):
                if key in sealed_yaml.CONTENT_KEYS:
                    where = f"in data/contents/{stem}.yaml" if split else "under `contents:`"
                    print(f"Product {name} in set {stem} has `{key}` at product level; it belongs {where}")
                else:
                    print(f"Product {name} in set {stem} has an unknown field `{key}`")
                failed = True
            if "category" not in p.keys():
                print(f"Product {name} in set {stem} missing category")
                failed = True
            elif p['category'] not in valid_categories:
                if p['category'] == "UNKNOWN":
                    print(f"Product {name} missing a valid category")
                    #pass
                else:
                    print(f"Product {name} has an invalid category: {p['category']}")
                    failed = True
            if "subtype" not in p.keys():
                print(f"Product {name} in set {stem} missing subtype")
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
    validate_references()
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

    for _, data in sealed_yaml.iter_sets():
        code = data["code"]
        products = data["products"]
        products_contents[code] = {}
        for name, entry in products.items():
            p = entry.get("contents")
            if not p:
                with open(status_file, "a") as f:
                    f.write(f"Product {code} - {name} missing contents\n")
                continue
            if set(p.keys()) == {"copy"}:
                p = products[p["copy"]].get("contents") or {}
            compiled_product = pc.product(copy.deepcopy(p), code, name)
            compiled_product.get_uuids(uuid_map)
            products_contents[code][name] = compiled_product
        if not products_contents[code]:
            products_contents.pop(code)

    deck_map = deck_links(products_contents)
    with atomic_write('outputs/deck_map.json') as outfile:
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
        validate_structure()
        uuid_map = build_uuid_map(args.mtgjson)
        if not uuid_map:
            raise SystemExit("Aborting: AllPrintings could not be loaded")
        rebuild_status_and_deck_map(uuid_map)
        print("🤖 status.txt and deck_map.json written")
    else:
        validate_structure()

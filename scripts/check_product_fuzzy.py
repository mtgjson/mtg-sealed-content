import argparse
import re
import sys
import yaml
from pathlib import Path
from thefuzz import fuzz

# Some terminals wrap pasted text in bracketed-paste markers (ESC[200~ ... ESC[201~);
# input() does not strip them, so remove them to keep pasted product names usable.
BRACKETED_PASTE_RE = re.compile(r"\x1b\[20[01]~")


def read_input(prompt=""):
    return BRACKETED_PASTE_RE.sub("", input(prompt))

parser = argparse.ArgumentParser(
    description="Interactively match review entries to known products."
)
parser.add_argument(
    "--skip",
    action="append",
    default=[],
    metavar="PATTERN",
    help="Skip review entries whose name contains PATTERN (case-insensitive). "
         "May be passed multiple times.",
)
parser.add_argument(
    "--auto",
    action="store_true",
    help="Non-interactively apply only high-confidence, unambiguous matches, "
         "leaving everything else in review.yaml for a manual pass.",
)
parser.add_argument(
    "--auto-score",
    type=int,
    default=96,
    metavar="N",
    help="Minimum fuzzy score (0-100) required to auto-match (default: 96).",
)
parser.add_argument(
    "--auto-margin",
    type=int,
    default=8,
    metavar="N",
    help="Minimum gap between the best and second-best score required to "
         "auto-match, to avoid false friends (default: 8).",
)
parser.add_argument(
    "--dry-run",
    action="store_true",
    help="With --auto, print the matches that would be applied without "
         "writing any files.",
)
args = parser.parse_args()
skip_patterns = [p.lower() for p in args.skip]

review_path = Path("data/review.yaml")
with open(review_path) as review_file:
    review_data = yaml.safe_load(review_file)


def remove_from_review(handled):
    """Drop the just-handled entry from the review data and persist it so a
    re-run does not prompt for the same product again."""
    name, identifiers = handled[0], handled[1]
    removed = False
    for provider_products in review_data.values():
        entry = provider_products.get(name)
        if entry is not None and entry.get("identifiers") == identifiers:
            del provider_products[name]
            removed = True
    if removed:
        with open(review_path, "w") as review_file:
            yaml.dump(review_data, review_file)


def apply_identifier(handled, target_name, target_file):
    """Write the review entry's identifier into the chosen known product.
    Returns (True, None) on success, or (False, existing) without writing when
    a different value is already set for one of the identifier keys (a conflict
    a human should resolve)."""
    with open(target_file) as product_file:
        import_products = yaml.safe_load(product_file)
    identifiers = import_products["products"][target_name].setdefault("identifiers", {})
    for key, value in handled[1].items():
        if key in identifiers and identifiers[key] != value:
            return False, identifiers[key]
    identifiers.update(handled[1])
    with open(target_file, "w") as product_file:
        yaml.dump(import_products, product_file)
    return True, None


def run_auto():
    """Auto-apply only high-confidence, unambiguous matches; anything below
    the score/margin thresholds is left in review.yaml for the manual pass."""
    matched = conflicts = ambiguous = 0
    for handled in list(review_products):
        # Drop [set code] tags and booster pack counts like "(36Packs)" for
        # matching (mtgjson names lack them), but keep years, player names and
        # "(N Starter Pack)" counts -- the count is the only thing telling a
        # single starter/tournament pack apart from its display box.
        query = re.sub(r"\[[^\]]*\]|\(\s*\d+\s*Packs?\s*\)", " ", handled[0], flags=re.I)
        query = re.sub(r"\s+", " ", query).strip()

        best_score = second_score = -1
        best = None
        for candidate in known_products:
            score = fuzz.token_sort_ratio(query, candidate[0])
            if score > best_score:
                second_score = best_score
                best_score, best = score, candidate
            elif score > second_score:
                second_score = score

        margin = best_score - second_score
        if best is None or best_score < args.auto_score or margin < args.auto_margin:
            ambiguous += 1
            continue

        # Edition code of the matched product (its data/products/<CODE>.yaml file)
        code = best[1].stem
        identifier = "/".join(str(v) for v in handled[1].values())

        if args.dry_run:
            print(f"[{best_score}/{margin}] {handled[0]!r} ({identifier}) -> {best[0]!r} [{code}]")
            matched += 1
            continue

        ok, _ = apply_identifier(handled, best[0], best[1])
        if ok:
            remove_from_review(handled)
            matched += 1
            print(f"matched [{best_score}/{margin}] {handled[0]!r} ({identifier}) -> {best[0]!r} [{code}]")
        else:
            conflicts += 1

    print(
        f"\nAuto-match: {matched} matched, {conflicts} conflicts, "
        f"{ambiguous + conflicts} left for review"
        + (" (dry run, nothing written)" if args.dry_run else "")
    )

review_products = []
skipped_count = 0
for provider_name, provider in review_data.items():
    for name, contents in provider.items():
        if any(p in name.lower() for p in skip_patterns):
            skipped_count += 1
            continue
        review_products.append((name, contents["identifiers"], contents.get("release_date", False), provider_name))

if skip_patterns:
    print(f"Skipping {skipped_count} review entries matching: {args.skip}")

known_products = []
for contentfile in Path("data/products").glob("*.yaml"):
    with open(contentfile, 'r') as known_file:
        known_data = yaml.safe_load(known_file)
    for product_name in known_data["products"].keys():
        known_products.append((product_name, contentfile))

if args.auto:
    run_auto()
    sys.exit(0)


def infer_product_definition(product_name):
    category = "UNKNOWN"
    subtype = "UNKNOWN"

    if "Draft Night Case" in product_name:
        category = "LIMITED_CASE"
        subtype = "DRAFT"
    elif "Draft Night" in product_name:
        category = "LIMITED"
        subtype = "DRAFT"
    elif "Gift Bundle Case" in product_name:
        category = "BUNDLE_CASE"
        subtype = "GIFT_BUNDLE"
    elif "Gift Bundle" in product_name:
        category = "BUNDLE"
        subtype = "GIFT_BUNDLE"
    elif "Jumpstart Booster Box Case" in product_name:
        category = "BOOSTER_CASE"
        subtype = "JUMPSTART"
    elif "Jumpstart Booster Box" in product_name:
        category = "BOOSTER_BOX"
        subtype = "JUMPSTART"
    elif "Jumpstart Booster Pack" in product_name:
        category = "BOOSTER_PACK"
        subtype = "JUMPSTART"
    elif "Beginner Box Case" in product_name:
        category = "BOX_SET"
        subtype = "STARTER"
    elif "Beginner Box" in product_name:
        category = "BOX_SET"
        subtype = "STARTER"
    elif "Scene Box Case" in product_name:
        category = "BOX_SET"
        subtype = "OTHER"
    elif "Scene Box" in product_name:
        category = "BOX_SET"
        subtype = "OTHER"
    elif "Theme Deck Display Case" in product_name:
        category = "DECK_BOX"
        subtype = "THEME"
    elif "Theme Deck Display" in product_name:
        category = "DECK_BOX"
        subtype = "THEME"
    elif "Welcome Deck" in product_name:
        category = "DECK"
        subtype = "WELCOME"
    elif "Prerelease Pack Case" in product_name:
        category = "LIMITED_CASE"
        subtype = "PRERELEASE"
    elif "Booster Box Case" in product_name:
        category = "BOOSTER_CASE"
    elif "Booster Box" in product_name:
        category = "BOOSTER_BOX"
    elif "Booster Pack" in product_name:
        category = "BOOSTER_PACK"
    elif "Bundle Case" in product_name:
        category = "BUNDLE_CASE"
    elif "Bundle" in product_name:
        category = "BUNDLE"
    elif "Set of" in product_name:
        category = "SUBSET"
    elif "Deck" in product_name:
        category = "DECK"
    elif "Prerelease" in product_name:
        category = "LIMITED"
    elif "Redemption" in product_name:
        category = "BOX_SET"

    if subtype == "UNKNOWN":
        if "Collector Booster" in product_name:
            subtype = "COLLECTOR"
        elif "Play Booster" in product_name:
            subtype = "PLAY"
        elif "Set Booster" in product_name:
            subtype = "SET"
        elif "Commander" in product_name:
            subtype = "COMMANDER"
        elif "Prerelease" in product_name:
            subtype = "PRERELEASE"
        elif "Theme" in product_name:
            subtype = "THEME"
        elif "Redemption" in product_name:
            subtype = "REDEMPTION"

    if "Secret Lair" in product_name and "Bundle" in product_name:
        category = "BOX_SET"
        subtype = "SECRET_LAIR_BUNDLE"

    return category, subtype

index = 0
offset = 0
while index < len(review_products):
    product = review_products[index]
    index += 1

    print(f"Finding similar products for {product[0]} {product[1]}")
    known_products.sort(key=lambda x: fuzz.token_sort_ratio(x[0], product[0]), reverse=True)
    for i in range(5):
        print(f"  {i} - {known_products[i + offset][0]}")

    try:
        product_check = read_input("Select action ('h' for help): ")
    except EOFError:
        sys.exit(1)

    # Look for the product name itself
    for i in range(len(known_products)):
        if product_check.strip().lower() == known_products[i][0].lower():
            product_check = "0"
            offset = i

    # Default selection
    if product_check == "":
        product_check = "0"

    if product_check == "q":
        break
    elif product_check == "s":
        offset = 0
        continue
    elif product_check == "m":
        index -= 1
        offset += 5
        if offset + 5 > len(known_products):
            offset = 0
    elif product_check == "b":
        index -= 1
        if index < 0:
            index = 0
        offset -= 5
        if offset < 0:
            print("NOTE: No previous choices available")
            offset = 0
    elif product_check == "u":
        index -= 2
        if index < 0:
            print("NOTE: There is no product before this one")
            index = 0
        offset = 0
    elif product_check == "i":
        with open("data/ignore.yaml", "r") as ignore_file:
            ignore_content = yaml.safe_load(ignore_file) or {}
        # The review entry's provider name is the ignore.yaml section name
        section = ignore_content.setdefault(product[3], {})
        for identifier in product[1].values():
            section[identifier] = product[0]
        with open("data/ignore.yaml", "w") as ignore_file:
            yaml.dump(ignore_content, ignore_file)
        remove_from_review(product)
    elif product_check in ["0","1","2","3","4"]:
        check_index = int(product_check) + offset
        if check_index >= len(known_products):
            print(f"NOTE: Selection out of range, max index is {len(known_products) - 1}")
            index -= 1
            continue
        product_link = known_products[check_index]
        with open(product_link[1], 'r') as product_file:
            import_products = yaml.safe_load(product_file)
        if "identifiers" not in import_products["products"][product_link[0]]:
            import_products["products"][product_link[0]]["identifiers"] = {}
        keep = True
        for key in product[1].keys():
            if key in import_products["products"][product_link[0]]["identifiers"] and import_products['products'][product_link[0]]['identifiers'][key] != product[1][key]:
                try:
                    ask = read_input(f"Confirm overwrite of existing id ({import_products['products'][product_link[0]]['identifiers'][key]})? [Y] ").lower()
                    keep = ask == "y" or ask == ""
                except EOFError:
                    sys.exit(1)
        if not keep:
            index -= 1
            continue
        import_products["products"][product_link[0]]["identifiers"].update(product[1])
        with open(product_link[1], 'w') as product_file:
            yaml.dump(import_products, product_file)
        remove_from_review(product)
    elif product_check == "c":
        try:
            set_code = read_input(f"OK, which set code? ").upper().strip()
        except EOFError:
            sys.exit(1)
        if set_code == "":
            print("set code is required, aborting")
            index -= 1
            continue

        try:
            product_name = read_input(f"Insert the product name or press Enter to use the loaded one: ").strip()
            if product_name == "":
                product_name = product[0]
        except EOFError:
            sys.exit(1)

        target_path = Path(f"data/products/{set_code}.yaml")
        if target_path.exists():
            with open(target_path, "r") as f:
                content = yaml.safe_load(f) or {}
            if product_name in content["products"].keys():
                print("Product already exists, not creating.")
                index -= 1
                continue
        else:
            content = {"code": set_code.lower(), "products": {}}

        category, subtype = infer_product_definition(product_name)

        content["products"][product_name] = {
            "category": category,
            "identifiers": dict(product[1]),
            "subtype": subtype,
        }

        with target_path.open("w") as product_file:
            yaml.dump(content, product_file)

        remove_from_review(product)
        known_products.append((product_name, target_path))
        print("Product added, don't forget to review and update default fields")

    else:
        index -= 1
        if product_check != "h":
            print(f"Invalid action: {product_check}")
        print("Available actions: q - quit / s - skip / i - ignore / m - more / b - back / u - undo / c - create / [0]124 - pick / use the exact name of the product")

    if product_check not in "mb":
        offset = 0

import sys
import yaml
from pathlib import Path
from thefuzz import fuzz

try:
    with open("data/review_temp.yaml") as review_file:
        review_data = yaml.safe_load(review_file)
except:
    with open("data/review.yaml", "r") as review_file:
        review_data = yaml.safe_load(review_file)

provmap = {
    "mcmId": "cardMarket",
    "cardtraderId": "cardTrader",
    "cardKingdomId": "cardKingdom",
    "tcgplayerProductId": "tcgplayer",
    "miniaturemarketId": "miniaturemarket",
    "scgId": "starcitygames",
    "csiId": "coolstuffinc",
    "abuId": "abugames",
    "tntId": "trollandtoad",
}

review_products = []
for provider in review_data.values():
    for name, contents in provider.items():
        review_products.append((name, contents["identifiers"], contents.get("release_date", False)))

known_products = []
for contentfile in Path("data/products").glob("*.yaml"):
    with open(contentfile, 'r') as known_file:
        known_data = yaml.safe_load(known_file)
    for product_name in known_data["products"].keys():
        known_products.append((product_name, contentfile))

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
        product_check = input("Select action ('h' for help): ")
    except EOFError:
        sys.exit(1)

    # Look for the product name itself
    for i in range(len(known_products)):
        if product_check.strip().lower() == known_products[i][0].lower():
            product_check = "0"
            offset = i

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
            ignore_content = yaml.safe_load(ignore_file)
        for provider, identifier in product[1].items():
            if provmap[provider] not in ignore_content:
                ignore_content[provmap[provider]] = {}
            ignore_content[provmap[provider]].update({identifier: product[0]})
        with open("data/ignore.yaml", "w") as ignore_file:
            yaml.dump(ignore_content, ignore_file)
    elif product_check in "01234":
        if product_check == "":
            product_check = "0"
        check_index = int(product_check) + offset
        product_link = known_products[check_index]
        with open(product_link[1], 'r') as product_file:
            import_products = yaml.safe_load(product_file)
        if "identifiers" not in import_products["products"][product_link[0]]:
            import_products["products"][product_link[0]]["identifiers"] = {}
        keep = True
        for key in product[1].keys():
            if key in import_products["products"][product_link[0]]["identifiers"] and import_products['products'][product_link[0]]['identifiers'][key] != product[1][key]:
                try:
                    ask = input(f"Confirm overwrite of existing id ({import_products['products'][product_link[0]]['identifiers'][key]})? [Y] ").lower()
                    keep = ask == "y" or ask == ""
                except EOFError:
                    sys.exit(1)
        if not keep:
            index -= 1
            continue
        import_products["products"][product_link[0]]["identifiers"].update(product[1])
        with open(product_link[1], 'w') as product_file:
            yaml.dump(import_products, product_file)
    elif product_check == "c":
        try:
            set_code = input(f"OK, which set code? ").upper().strip()
        except EOFError:
            sys.exit(1)
        if set_code == "":
            print("set code is required, aborting")
            index -= 1
            continue

        try:
            product_name = input(f"Insert the product name or press Enter to use the loaded one: ").strip()
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
            content = {}
            content.setdefault("code", set_code)
            content.setdefault("products", {})

        category = "UNKNOWN"
        if "Booster Box Case" in product_name:
            category = "BOOSTER_CASE"
        elif "Booster Box" in product_name:
            category = "BOOSTER_BOX"
        elif "Booster Pack" in product_name:
            category = "BOOSTER_PACK"
        elif "Bundle" in product_name:
            category = "BUNDLE"
        elif "Set of" in product_name:
            category = "SUBSET"
        elif "Deck" in product_name:
            category = "DECK"
        elif "Prerelease" in product_name:
            category = "LIMITED"

        subtype = "UNKNOWN"
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
            subytpe = "THEME"

        if "Secret Lair" in product_name and "Bundle" in product_name:
            category = "BOX_SET"
            subtype = "SECRET_LAIR_BUNDLE"

        content["products"][product_name] = {
            "category": category,
            "identifiers": dict(product[1]),
            "subtype": subtype,
        }

        with target_path.open("w") as product_file:
            yaml.dump(content, product_file)

        known_products.append((product_name, str(target_path)))
        print("Product added, don't forget to review and update default fields")

    else:
        index -= 1
        if product_check != "h":
            print(f"Invalid action: {product_check}")
        print("Available actions: q - quit / s - skip / i - ignore / m - more / b - back / u - undo / c - create / [0]124 - pick / use the exact name of the product")

    if product_check not in "mb":
        offset = 0

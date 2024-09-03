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

    print(f"Finding similar products for {product[0]}")
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
                    ask = input("Confirm overwrite of existing id? [Y] ").lower()
                    keep = ask == "y" or ask == ""
                except EOFError:
                    sys.exit(1)
        if not keep:
            index -= 1
            continue
        import_products["products"][product_link[0]]["identifiers"].update(product[1])
        if product[2]:
            if "release_date" not in import_products["products"][product_link[0]]:
                import_products["products"][product_link[0]]["release_date"] = product[2]
            elif import_products["products"][product_link[0]]["release_date"] != product[2]:
                d = import_products["products"][product_link[0]]["release_date"]
                try:
                    ask = input(f"Update current date {d} with new date {product[2]}? [Y] ").lower()
                    check = ask == "y" or ask == ""
                except EOFError:
                    sys.exit(1)
                if check:
                    import_products["products"][product_link[0]]["release_date"] = product[2]
        with open(product_link[1], 'w') as product_file:
            yaml.dump(import_products, product_file)
    else:
        index -= 1
        if product_check != "h":
            print(f"Invalid action: {product_check}")
        print("Available actions: q - quit / s - skip / i - ignore / m - more / b - back / u - undo / [0]124 - pick / use the exact name of the product")

    if product_check not in "mb":
        offset = 0

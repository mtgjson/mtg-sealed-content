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
    "miniaturemarketId": "miniaturemarket"
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

for product in review_products:
    print(f"Finding similar products for {product[0]}")
    known_products.sort(key=lambda x: fuzz.token_sort_ratio(x[0], product[0]), reverse=True)
    for i in range(5):
        print(f"  {i} - {known_products[i][0]}")
    product_check = input("Which product or action? ")
    if product_check == "q":
        break
    elif product_check == "s":
        continue
    elif product_check == "i":
        with open("data/ignore.yaml", "r") as ignore_file:
            ignore_content = yaml.safe_load(ignore_file)
        for provider, identifier in product[1].items():
            if provmap[provider] not in ignore_content:
                ignore_content[provmap[provider]] = {}
            ignore_content[provmap[provider]].update({int(identifier): product[0]})
        with open("data/ignore.yaml", "w") as ignore_file:
            yaml.dump(ignore_content, ignore_file)
    elif product_check in "01234":
        check_index = int(product_check)
        product_link = known_products[check_index]
        with open(product_link[1], 'r') as product_file:
            import_products = yaml.safe_load(product_file)
        if "identifiers" not in import_products["products"][product_link[0]]:
            import_products["products"][product_link[0]]["identifiers"] = {}
        import_products["products"][product_link[0]]["identifiers"].update(product[1])
        if product[2]:
            if "release_date" not in import_products["products"][product_link[0]]:
                import_products["products"][product_link[0]]["release_date"] = product[2]
            elif import_products["products"][product_link[0]]["release_date"] != product[2]:
                d = import_products["products"][product_link[0]]["release_date"]
                check = input(f"Update current date {d} with new date {product[2]}? ")
                if "y" in check:
                    import_products["products"][product_link[0]]["release_date"] = product[2]
        with open(product_link[1], 'w') as product_file:
            yaml.dump(import_products, product_file)

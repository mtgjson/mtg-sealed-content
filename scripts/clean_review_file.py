import yaml
from pathlib import Path

with open("data/ignore.yaml", "r") as ifile:
    ignore_data = yaml.safe_load(ifile)

provmap = {
    "cardMarket": "mcmId",
    "cardTrader": "cardtraderId",
    "cardKingdom": "cardKingdomId",
    "tcgplayer": "tcgplayerProductId",
    "miniaturemarket": "miniaturemarketId",
    "starcitygames": "scgId"
}

check_data = {provmap[provider]: set([str(k) for k in products.keys()]) for provider, products in ignore_data.items()}

for known_file in Path("data/products").glob("*.yaml"):
    with open(known_file, "r") as kfile:
        known_product = yaml.safe_load(kfile)
    for product in known_product["products"].values():
        for provider, id in product.get("identifiers", {}).items():
            if provider not in check_data:
                check_data[provider] = set()
            check_data[provider].add(str(id))

with open("data/review.yaml", "r") as rfile:
    review_current = yaml.safe_load(rfile)

review_new = {}

for provider, products in review_current.items():
    review_new[provider] = {}
    for p_name, info in products.items():
        known = False
        for prov, id in info["identifiers"].items():
            if prov in check_data and str(id) in check_data[prov]:
                known = True
        if not known:
            review_new[provider][p_name] = info

with open("data/review_temp.yaml", "w") as rfile:
    yaml.dump(review_new, rfile)

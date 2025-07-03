import yaml
from pathlib import Path
from thefuzz import fuzz
import ijson
import requests
import sys

url = r"https://mtgjson.com/api/v5/SLD.json"
r = requests.get(url, stream=True)
uuids = {}
parser = ijson.parse(r.content)

decks = []

for prefix, event, value in parser:
    if prefix == "data.decks.item" and event == "start_map":
        decks.append({"count": 0})
    elif prefix == "data.decks.item.name" and event == "string":
        decks[-1]["name"] = value
    elif prefix == "data.decks.item.mainBoard.item.count" and event == "number":
        decks[-1]["count"] += int(value)
    elif prefix == "data.decks.item.commander.item.count" and event == "number":
        decks[-1]["count"] += int(value)
    elif prefix == "data.decks.item.sideBoard.item.count" and event == "number":
        decks[-1]["count"] += int(value)

with open("data/contents/SLD.yaml", 'r') as sfile:
    sld_products = yaml.safe_load(sfile)

product_names = list(sld_products["products"].keys())
mapped_decks = {}
for k, v in sld_products["products"].items():
    if "deck" in v:
        for dk in v["deck"]:
            mapped_decks[dk["name"]] = k

index = 0
offset = 0
while index < len(decks):
    deck = decks[index]
    index += 1

    if deck["name"] in mapped_decks:
        continue

    print(f"Finding similar products for {deck['name']}")
    product_names.sort(key=lambda x: fuzz.token_sort_ratio(x, deck["name"]), reverse=True)
    for i in range(5):
        print(f"  {i} - {product_names[i + offset]}")
    
    try:
        product_check = input("Select action ('h' for help): ")
    except EOFError:
        sys.exit(1)
    
    # Look for the product name itself
    for i in range(len(product_names)):
        if product_check.strip().lower() == product_names[i].lower():
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
        if offset + 5 > len(product_names):
            offset = 0
    elif product_check == "u":
        index -= 2
        if index < 0:
            print("NOTE: There is no product before this one")
            index = 0
        offset = 0
    elif product_check in "01234":
        if product_check == "":
            product_check = "0"

        check_index = int(product_check) + offset
        p_name = product_names[check_index]
        if isinstance(sld_products["products"][p_name], list):
            sld_products["products"][p_name] = {}
        if "card_count" in sld_products["products"][p_name]:
            keep = True
            if sld_products["products"][p_name]['card_count'] != deck["count"]:
                try:
                    ask = input(f"Replace count {sld_products['products'][p_name]['card_count']} with {deck['count']}? [Y]: ")
                    keep = ask == "y" or ask == ""
                except EOFError:
                    sys.exit(1)
            if keep:
                sld_products["products"][p_name]['card_count'] = deck["count"]
        else:
            sld_products["products"][p_name]['card_count'] = deck["count"]

        if "deck" not in sld_products["products"][p_name]:
            sld_products["products"][p_name]["deck"] = [{"name": deck["name"], "set": "sld"}]

        if ("card" not in sld_products["products"][p_name]) and ("pack" not in sld_products["products"][p_name]) and ("variable" not in sld_products["products"][p_name]):
            sld_products["products"][p_name]["other"] = [{"name": "Bonus card unknown"}]

        print(sld_products["products"][p_name])
    else:
        index -= 1
        if product_check != "h":
            print(f"Invalid action: {product_check}")
        print("Available actions: q - quit / s - skip / m - more / u - undo / [0]124 - pick / use the exact name of the product")

    if product_check not in "mb":
        offset = 0

with open("data/contents/SLD.yaml", 'w') as sfile:
    yaml.dump(sld_products, sfile)

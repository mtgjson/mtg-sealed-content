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

for d in decks:
    if d["name"] in mapped_decks:
        continue
    product_names.sort(key=lambda x: fuzz.token_sort_ratio(x, d["name"]), reverse=True)
    print(f"Finding similar products for {d['name']}")
    for i in range(5):
        print(f"  {i} - {product_names[i]}")
    
    try:
        product_number = input("Select action ('h' for help): ")
    except EOFError:
        sys.exit(1)
    
    if product_number == "q":
        break
    elif product_number == "s":
        continue
    elif product_number in "01234":
        p_name = product_names[int(product_number)]
        if isinstance(sld_products["products"][p_name], list):
            sld_products["products"][p_name] = {}
        if "card_count" in sld_products["products"][p_name]:
            if sld_products["products"][p_name]['card_count'] != d["count"]:
                rp = input(f"Replace count {sld_products['products'][p_name]['card_count']} with {d['count']}? (y/n): ")
                if rp == "y":
                    sld_products["products"][p_name]['card_count'] = d["count"]
        else:
            sld_products["products"][p_name]['card_count'] = d["count"]
        if "deck" not in sld_products["products"][p_name]:
            sld_products["products"][p_name]["deck"] = [{"name": d["name"], "set": "sld"}]
        if ("card" not in sld_products["products"][p_name]) and ("pack" not in sld_products["products"][p_name]) and ("variable" not in sld_products["products"][p_name]):
            sld_products["products"][p_name]["other"] = [{"name": "Bonus card unknown"}]
        print(sld_products["products"][p_name])

with open("data/contents/SLD.yaml", 'w') as sfile:
    yaml.dump(sld_products, sfile)

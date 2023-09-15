import yaml
import product_classes as pc
from pathlib import Path
import json
import ijson
import requests
from tqdm import tqdm


def set_to_json(set_content):
    return {k: v.toJson() for k, v in set_content.items()}


def build_uuid_map():
    url = "https://mtgjson.com/api/v5/AllPrintings.json"
    r = requests.get(url, stream=True)
    uuids = {}
    parser = ijson.parse(r.content)
    current_set = ""
    status = ""
    identifier = ""
    uuid = ""
    for prefix, event, value in tqdm(parser):
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
                identifier = ""
                uuid = ""
            elif prefix == f"data.{current_set}.sealedProduct.item.name":
                identifier = value
            elif prefix == f"data.{current_set}.sealedProduct.item.uuid":
                uuid = value
            elif (
                    prefix == f"data.{current_set}.sealedProduct.item"
                    and event == "end_map"
            ):
                uuids[ccode]["sealedProduct"][identifier] = uuid
        elif status == "cards":
            if prefix == f"data.{current_set}.cards.item" and event == "start_map":
                identifier = ""
                uuid = ""
            elif prefix == f"data.{current_set}.cards.item.number":
                identifier = value
            elif prefix == f"data.{current_set}.cards.item.uuid":
                uuid = value
            elif prefix == f"data.{current_set}.cards.item" and event == "end_map":
                uuids[ccode]["cards"][identifier] = uuid
    return uuids


def deck_links(all_products):
    deck_mapper = {}
    for set_contents in all_products.values():
        for product_contents in set_contents.values():
            for deck in product_contents.deck:
                if deck.set not in deck_mapper:
                    deck_mapper[deck.set] = {}
                if deck.name not in deck_mapper[deck.set]:
                    deck_mapper[deck.set][deck.name] = []
                deck_mapper[deck.set][deck.name].append(product_contents.uuid)
    return deck_mapper


def main(contentFolder):
    uuid_map = build_uuid_map()
    products_contents = {}
    for set_file in contentFolder.glob("*.yaml"):
        with open(set_file, 'rb') as f:
            contents = yaml.safe_load(f)

        products_contents[set_file.stem.lower()] = {}
        for name, p in contents["products"].items():
            if not p:
                p = {}
            if set(p.keys()) == {"copy"}:
                p = contents["products"][p["copy"]]
            compiled_product = pc.product(p, set_file.stem, name)
            compiled_product.get_uuids(uuid_map)
            products_contents[set_file.stem.lower()][name] = compiled_product
    
    with open("outputs/contents.json", "w") as outfile:
        json.dump({k: set_to_json(v) for k, v in products_contents.items()}, outfile)
    
    deck_map = deck_links(products_contents)
    
    with open("outputs/deck_map.json", "w") as outfile:
        json.dump(deck_map, outfile)


if __name__ == "__main__":
    main(Path("data/contents/"))

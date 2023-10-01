import pathlib

import ijson
import json
import yaml
from pathlib import Path
import os
import os.path as path
import time
import requests


def get_cardKingdom():
    sealed_url = "https://api.cardkingdom.com/api/sealed_pricelist"
    r = requests.get(sealed_url)
    ck_data = json.loads(r.content)
    return ck_data['meta']['base_url'], ck_data['data']


def main():
    url = "https://mtgjson.com/api/v5/AllPrintings.json"
    r = requests.get(url, stream=True)

    alt_codes = {"con_": "con"}
    r_alt_codes = {"CON": "CON_"}

    # Set up known product objects
    ck_no_url = dict()
    with open('data/ignore.yaml') as ignore_file:
        ignore = yaml.safe_load(ignore_file)
    ck_ids = set(ignore['cardKingdom'].keys())
    tg_ids = set(ignore['tcgplayer'].keys())
    ck_review = dict()
    tg_review = dict()
    
    for known_file in Path("data/products").glob("*.yaml"):
        with open(known_file, 'rb') as yfile:
            loaded_data = yaml.safe_load(yfile)
        ck_ids.update({p['identifiers'].get('cardKingdomId', None) for p in loaded_data['products'].values() if "cardKingdom" in p.get('purchase_url', {})})
        ck_no_url.update({p['identifiers'].get('cardKingdomId', None):known_file for p in loaded_data['products'].values() if "cardKingdom" not in p.get('purchase_url', {})})
        ck_ids.update({p['identifiers'].get('tcgplayerProductId', None) for p in loaded_data['products'].values()})
    
    # Load Card Kingdom products
    urlbase, ck_products = get_cardKingdom()
    for product in ck_products:
        if str(product['id']) in ck_ids or product['id'] in ck_ids:
            continue
        elif str(product['id']) in ck_no_url or product['id'] in ck_no_url:
            file = ck_no_url[str(product['id'])]
            with open(file, 'rb') as yfile:
                loaded_data = yaml.safe_load(yfile)
            for p_name in loaded_data['products'].keys():
                if str(product['id']) == loaded_data['products'][p_name]['identifiers'].get('cardKingdomId', None):
                    if 'purchase_url' not in loaded_data['products'][p_name]:
                        loaded_data['products'][p_name]['purchase_url'] = {}
                    loaded_data['products'][p_name]['purchase_url']['cardKingdom'] = urlbase + product['url']
            with open(file, 'w') as yfile:
                yaml.dump(loaded_data, yfile)
        else:
            ck_review.update({product['name']: {"identifiers": {"cardKingdomId": str(product['id'])}}})
       
    # Load TCGPlayer products [unknown]
    
    # Dump new products into the review section    
    with open('data/review.yaml', 'w') as yfile:
        yaml.dump({'cardKingdom': ck_review, 'tcgplayer': tg_review}, yfile)
    
    # Add any new/modified products to the contents files
    for set_file in Path("data/products").glob("*.yaml"):
        with open(set_file, 'r') as yfile:
            load_data = yaml.safe_load(yfile)
        with open(Path("data/contents").joinpath(set_file.name), 'r') as yfile:
            content_data = yaml.safe_load(yfile)
        for p_name in load_data['products'].keys():
            if p_name not in content_data['products']:
                content_data['products'][p_name] = []
        removes = []
        for p_name, p_cont in content_data['products'].items():
            if not p_cont and p_name not in load_data['products']:
                removes.append(p_name)
        for n in removes:
            content_data['products'].pop(n)
        with open(Path("data/contents").joinpath(set_file.name), 'w') as yfile:
            yaml.dump(content_data, yfile)


if __name__ == "__main__":
    main()

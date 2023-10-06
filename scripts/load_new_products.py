import pathlib
import ijson
import json
import yaml
from pathlib import Path
import os
import os.path as path
import time
import requests
from datetime import datetime
import sys


def get_cardKingdom():
    sealed_url = "https://api.cardkingdom.com/api/sealed_pricelist"
    r = requests.get(sealed_url)
    ck_data = json.loads(r.content)
    return ck_data['meta']['base_url'], ck_data['data']


def tcgdownload(url, params, api_version, auth_code):
    header = {
        "Authorization": f"Bearer {auth_code}"
    } # Need to figure out the correct headers for TCG API
     # Need to figure out the correct version for TCG API
    r = requests.get(url.replace("[API_VERSION]", api_version), params=params, headers=header)
    #print(r.ok)
    return r.content


def get_tcgplayer(api_version, auth_code):
    # get set ids
    magic_set_ids = []
    api_offset = 0
    product_types = [
        "Booster Box",
        "Booster Pack",
        "Sealed Products",
        "Intro Pack",
        "Fat Pack",
        "Box Sets",
        "Precon/Event Decks",
        "Magic Deck Pack",
        "Magic Booster Box Case",
        "All 5 Intro Packs",
        "Intro Pack Display",
        "3x Magic Booster Packs",
        "Booster Battle Pack",
    ]

    while True:
        api_response = tcgdownload(
            "https://api.tcgplayer.com/[API_VERSION]/catalog/categories/1/groups",
            {"offset": str(api_offset)},
            api_version,
            auth_code
        )

        if not api_response:
            # No more entries
            break

        response = json.loads(api_response)
        if not response["results"]:
            # Something went wrong
            break

        for magic_set in response["results"]:
            magic_set_ids.append((magic_set["groupId"], magic_set["name"]))

        api_offset += len(response["results"])
    
    sealed_data = []
    for group_id in magic_set_ids:
        api_offset=0
        print(group_id)
        while True:
            api_response = tcgdownload(
                "https://api.tcgplayer.com/catalog/products",
                {
                    "offset": str(api_offset),
                    "limit": 100,
                    "categoryId": 1,
                    "groupId": str(group_id[0]),
                    "getExtendedFields": True,
                    "productTypes": ",".join(product_types),
                },
                api_version,
                auth_code
            )

            if not api_response:
                # No more entries
                break

            try:
                response = json.loads(api_response)
            except json.decoder.JSONDecodeError:
                print(f"Unable to decode TCGPlayer API Response {api_response}")
                break

            if not response["results"]:
                print(
                    f"Issue with Sealed Product for Group ID: {group_id}: {response}"
                )
                break
            
            cleaned_data = [
                {
                    "name": product['cleanName'],
                    "id": product['productId'], 
                    "releaseDate": product["presaleInfo"].get("releasedOn")
                } for product in response['results']
            ]
            sealed_data.extend(cleaned_data)
            api_offset += len(response["results"])

            # If we got fewer results than requested, no more data is needed
            if len(response["results"]) < 100:
                print(f"Found {api_offset} products")
                break
    return sealed_data


def get_tcg_auth_code(secret):
    if not secret:
        return "v1.39.0", ""
    tcg_post = requests.post(
        "https://api.tcgplayer.com/token",
        data={
            "grant_type": "client_credentials",
            "client_id": secret.get("client_id"),
            "client_secret": secret.get("client_secret"),
        },
        timeout=60,
    )
    if not tcg_post.ok:
        print(f"Unable to contact TCGPlayer. Reason: {tcg_post.reason}")
        return ""
    request_as_json = json.loads(tcg_post.text)
    
    api_version = secret.get("api_version", "v1.39.0")
    
    return api_version, str(request_as_json.get("access_token", ""))


def main(secret):
    url = "https://mtgjson.com/api/v5/AllPrintings.json"
    r = requests.get(url, stream=True)
    
    api_version, tcg_auth_code = get_tcg_auth_code(secret)

    alt_codes = {"con_": "con"}
    r_alt_codes = {"CON": "CON_"}

    # Set up known product objects
    with open('data/ignore.yaml') as ignore_file:
        ignore = yaml.safe_load(ignore_file)
    ck_ids = set(ignore['cardKingdom'].keys())
    tg_ids = set(ignore['tcgplayer'].keys())
    ck_review = dict()
    tg_review = dict()
    
    for known_file in Path("data/products").glob("*.yaml"):
        with open(known_file, 'rb') as yfile:
            loaded_data = yaml.safe_load(yfile)
        ck_ids.update({p['identifiers'].get('cardKingdomId', None) for p in loaded_data['products'].values()})
        tg_ids.update({p['identifiers'].get('tcgplayerProductId', None) for p in loaded_data['products'].values()})
    
    # Load Card Kingdom products
    urlbase, ck_products = get_cardKingdom()
    for product in ck_products:
        if str(product['id']) in ck_ids or product['id'] in ck_ids:
            continue
        else:
            ck_review.update({product['name']: {"identifiers": {"cardKingdomId": str(product['id'])}}})
       
    # Load TCGPlayer products [unknown]
    tg_products = get_tcgplayer(api_version, tcg_auth_code)
    for product in tg_products:
        if str(product['id']) in tg_ids or product['id'] in tg_ids:
            continue
        else:
            tg_review[product['name']] = {
                "identifiers": {"tcgplayerProductId": product['id']}
            }
            if product['releaseDate']:
                date_obj = datetime.strptime(product['releaseDate'], '%Y-%m-%dT%H:%M:%S')
                tg_review[product['name']]['release_date'] = date_obj.strftime("%Y-%m-%d")
    
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
    try:
        secret = json.loads(" ".join(sys.argv[1:])[1:-1])
    except IndexError:
        secret = {}
    main(secret)

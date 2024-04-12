import json
import sys
import os
import io
from datetime import datetime
from pathlib import Path

import mkmsdk.exceptions
from mkmsdk.api_map import _API_MAP
from mkmsdk.mkm import Mkm

import requests
import yaml
import csv
import base64
import zlib


def get_cardKingdom():
    sealed_url = "https://api.cardkingdom.com/api/sealed_pricelist"
    r = requests.get(sealed_url)
    ck_data = json.loads(r.content)
    output_data = ck_data['data']
    output_data = [x for x in output_data if "Set (Factory Sealed)" not in x['name']]
    output_data = [x for x in output_data if "Pure Bulk:" not in x['name']]
    return output_data


def tcgdownload(url, params, api_version, auth_code):
    header = {
        "Authorization": f"Bearer {auth_code}"
    }  # Need to figure out the correct headers for TCG API
    # Need to figure out the correct version for TCG API
    r = requests.get(
        url.replace("[API_VERSION]", api_version), params=params, headers=header
    )
    # print(r.ok)
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
            auth_code,
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
        api_offset = 0
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
                auth_code,
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
                print(f"Issue with Sealed Product for Group ID: {group_id}: {response}")
                break

            cleaned_data = [
                {
                    "name": product["cleanName"],
                    "id": product["productId"],
                    "releaseDate": product["presaleInfo"].get("releasedOn"),
                }
                for product in response["results"]
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


def get_mkm_productsfile(secret):
    try:
        os.environ["MKM_APP_TOKEN"] = secret.get("app_token")
        os.environ["MKM_APP_SECRET"] = secret.get("app_secret")
        os.environ["MKM_ACCESS_TOKEN"] = secret.get("access_token") or ""
        os.environ["MKM_ACCESS_TOKEN_SECRET"] = secret.get("access_token_secret") or ""
    except TypeError:
        print(f"Incorrectly coded MKM token")
        return ""

    mkm_connection = Mkm(_API_MAP["2.0"]["api"], _API_MAP["2.0"]["api_root"])

    try:
        mkm_response = mkm_connection.market_place.product_list().json()
    except mkmsdk.exceptions.ConnectionError as exception:
        print(f"Unable to download MKM correctly: {exception}")
        return ""

    product_data = base64.b64decode(mkm_response["productsfile"])  # Un-base64
    product_data = zlib.decompress(product_data, 16 + zlib.MAX_WBITS)  # Un-gzip
    decoded_data = product_data.decode("utf-8")  # byte array to string
    return io.StringIO(decoded_data)


def get_cardmarket(productsfile):
    category_types = [
        "Magic Booster",
        "Magic Display",
        "Magic Intropack",
        "Magic Fatpack",
        "Magic Theme Deck Display",
        "Magic TournamentPack",
        "Magic Starter Deck",
        "MtG Set"
    ]

    # "MtG Set" contains a mix of sealed product and bundles of cards
    # This list filters the bundles of cards away from all sets
    skip_tags = [
        "Accessories set",
        "Art Cards Set",
        "Art Series Set",
        "Attraction Set",
        "Borderless Planeswalkers Set",
        "Common Set",
        "Contraption Set",
        "CustomSet",
        "Dual Lands Set",
        "Extended-Art Frames set",
        "Fetchland Set",
        "GnD Cards",
        "Land Set",
        "Masterpiece Set",
        "Mythic Set",
        "Oversized",
        "P9 Set",
        "Phenomena Set",
        "Plane Set",
        "Planechase Set",
        "Planes Set",
        "Promo Pack",
        "Rare Set",
        "Relic Tokens",
        "Scene Set",
        "Scheme Set",
        "Showcase Frame set",
        "Special set",
        "Sticker Set",
        "Summary Set",
        "Time Shifted Set",
        "Timeshifted Set",
        "Token Set", # we can't use "Token" because it is a common word
        "Tokens Set",
        "Tokens for MTG",
        "Uncommon Set",
    ]

    # "MtG Set" has a suffix "Full Set" that implies "bundles of cards"
    # except for these two series where it implies "sealed" instead
    full_set_ok = [
        "Signature Spellbook",
        "From the Vault",
    ]

    sealed_data = []

    # idProduct,Name,"Category ID","Category","Expansion ID","Metacard ID","Date Added"
    reader = csv.reader(productsfile)
    for row in reader:
        if row[3] not in category_types:
            continue

        if any(tag.lower() in row[1].lower() for tag in skip_tags):
            continue
        if "Full Set" in row[1] and not any(tag in row[1] for tag in full_set_ok):
            continue
        if "Secret Lair" in row[1] and " Set" in row[1]:
            continue
        if "Secret Lair" in row[1] and " Booster" in row[1]:
            continue

        sealed_data.extend([
            {
                "name": row[1],
                "id": row[0],
                "releaseDate": row[6],
            }
        ])

    return sealed_data


def load_cardkingdom(secret):
    return get_cardKingdom()


def preload_tcgplayer(secret):
    api_version, tcg_auth_code = get_tcg_auth_code(secret)
    secret["api_version"] = api_version
    secret["tcg_auth_code"] = tcg_auth_code


def load_tcgplayer(secret):
    api_version = secret.get("api_version")
    tcg_auth_code = secret.get("tcg_auth_code")
    return get_tcgplayer(api_version, tcg_auth_code)


def preload_cardmarket(secret):
    mkm_productsfile = get_mkm_productsfile(secret)
    secret["mkm_productsfile"] = mkm_productsfile


def load_cardmarket(secret):
    mkm_productsfile = secret.get("mkm_productsfile")
    return get_cardmarket(mkm_productsfile)


providers_dict = {
    "cardKingdom": {
        "identifier": "cardKingdomId",
        "load_func": load_cardkingdom,
    },
    "tcgplayer": {
        "identifier": "tcgplayerProductId",
        "preload_func": preload_tcgplayer,
        "load_func": load_tcgplayer,
    },
    "cardMarket": {
        "identifier": "mcmId",
        "preload_func": preload_cardmarket,
        "load_func": load_cardmarket,
    },
}


def main(secret):
    # Load any prerequisite data (auth or similar)
    for provider in providers_dict.values():
        if provider.get("disabled") or provider.get("preload_func") is None:
            continue
        provider["preload_func"](secret)

    # Set up known product objects
    with open("data/ignore.yaml") as ignore_file:
        ignore = yaml.safe_load(ignore_file)

    ids = dict()
    reviews = dict()

    # Set up the list of ids and items to review for each provider
    for key, provider in providers_dict.items():
        provider_ids = set(str(x) for x in ignore[key].keys())
        ids[key]= provider_ids
        reviews[key] = dict()

    # Load data from the known products
    for known_file in Path("data/products").glob("*.yaml"):
        with open(known_file, "rb") as yfile:
            loaded_data = yaml.safe_load(yfile)
        with open(known_file, "w") as yfile:
            yaml.dump(loaded_data, yfile)

        # For each provider, load every known id
        for key, provider in providers_dict.items():
            if provider.get("disabled"):
                continue
            ids[key].update(
                {
                    str(p["identifiers"][provider["identifier"]])
                    for p in loaded_data["products"].values()
                    if "identifiers" in p and p["identifiers"].get(provider["identifier"])
                }
            )

    # Update all the ids
    for key, provider in providers_dict.items():
        if provider.get("disabled"):
            continue
        products = provider["load_func"](secret)

        for product in products:
            if str(product["id"]) in ids[key]:
                continue

            reviews[key][product["name"]] = {
                "identifiers": {provider["identifier"]: str(product["id"])},
                "category": "UNKNOWN",
                "subtype": "UNKNOWN"
            }
            if product.get("releaseDate") != None:
                try:
                    date_obj = datetime.strptime(product["releaseDate"], "%Y-%m-%dT%H:%M:%S")
                except Exception:
                    date_obj = datetime.strptime(product["releaseDate"], "%Y-%m-%d %H:%M:%S")
                    pass
                reviews[key][product["name"]]["release_date"] = date_obj.strftime("%Y-%m-%d")

    # Dump new products into the review section
    with open("data/review.yaml", "w") as yfile:
        yaml.dump(reviews, yfile)

    # Add any new/modified products to the contents files
    for set_file in Path("data/products").glob("*.yaml"):
        with open(set_file, "r") as yfile:
            load_data = yaml.safe_load(yfile)
        cpath = Path("data/contents").joinpath(set_file.name)
        if cpath.is_file():
            with open(cpath, "r") as yfile:
                content_data = yaml.safe_load(yfile)
        else:
            content_data = {"code": load_data['code'], "products":{}}
        for p_name in load_data["products"].keys():
            if p_name not in content_data["products"]:
                content_data["products"][p_name] = []
        removes = []
        for p_name, p_cont in content_data["products"].items():
            if not p_cont and p_name not in load_data["products"]:
                removes.append(p_name)
        for n in removes:
            content_data["products"].pop(n)
        with open(Path("data/contents").joinpath(set_file.name), "w") as yfile:
            yaml.dump(content_data, yfile)


if __name__ == "__main__":
    try:
        secret = json.loads(" ".join(sys.argv[1:])[1:-1])
    except Exception:
        print("Unable to parse auth - only non-authenticated requests will succeed")
        secret = {}
        pass

    if secret.get("client_id") == None or secret.get("client_secret") == None:
        print("TCGplayer is disabled due missing auth")
        providers_dict["tcgplayer"]["disabled"] = True

    if secret.get("app_token") == None or secret.get("app_secret") == None:
        print("Cardmarket is disabled due missing auth")
        providers_dict["cardMarket"]["disabled"] = True

    main(secret)

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

from bs4 import BeautifulSoup
from urllib.parse import urlparse

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


def get_cardmarket():
    product_list_url = "https://downloads.s3.cardmarket.com/productCatalog/productList/products_nonsingles_1.json"
    r = requests.get(product_list_url)
    mkm_data = json.loads(r.content)
    product_list = mkm_data["products"]

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
        "Creature Forge",
        "CustomSet",
        "Dual Lands Set",
        "Empty",
        "Extended-Art Frames set",
        "Fetchland Set",
        "GnD Cards",
        "Land Set",
        "LocalProAlters Tokens",
        "Masterpiece Set",
        "Mythic Set",
        "Oversized",
        "P9 Set",
        "Phenomena Set",
        "Plane Set",
        "Planechase Set",
        "Planes Set",
        "Prerelease Promo",
        "Promo Pack",
        "Rare Set",
        "Relic Tokens",
        "SAWATARIX",
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
        "Duel Deck"
    ]

    sealed_data = []

    # idProduct,Name,"Category ID","Category","Expansion ID","Metacard ID","Date Added"
    for product in product_list:
        if product["categoryName"] not in category_types:
            continue

        product_name = product["name"]
        if any(tag.lower() in product_name.lower() for tag in skip_tags):
            continue
        if "Full Set" in product_name and not any(tag in product_name for tag in full_set_ok):
            continue
        if "Secret Lair" in product_name and " Set" in product_name:
            continue
        if "Secret Lair" in product_name and " Booster" in product_name:
            continue

        sealed_data.extend([
            {
                "name": product_name,
                "id": product["idProduct"],
                "releaseDate": product["dateAdded"],
            }
        ])

    print(f"Parsed {len(sealed_data)} products")

    return sealed_data


def ctdownload(url, params, token):
    header = {
        "Authorization": f"Bearer {token}"
    }
    r = requests.get(url, params=params, headers=header)
    return r.content


def load_cardtrader(secret):
    token = secret.get("ct_token")

    allExpansions = json.loads(ctdownload("https://api.cardtrader.com/api/v2/expansions", None, token))

    # game_id = 1 -> mtg
    mtgExpansions = [x for x in allExpansions if x["game_id"] == 1]

    # all the categories containing sealed product
    category_types = [4,5,7,10,13,17,23,24]

    skip_tags = [
        "Promo Pack",
        "Basic Land Pack",
        "Relic Tokens",
        "Creature Forge",
    ]

    sld_skip_tags = [
        "Booster",
        "Set",
        "Serialized",
    ]

    sealed_data = []

    for exp in mtgExpansions:
        print(f"({exp['id']}, '{exp['name']}')")

        blueprints = json.loads(ctdownload("https://api.cardtrader.com/api/v2/blueprints/export", {"expansion_id": exp["id"]}, token))

        count = 0
        for blueprint in blueprints:
            if not isinstance(blueprint, dict):
                print(f"Product {blueprint} incorrectly formatted")
                continue
            if blueprint["game_id"] != 1:
                continue
            if blueprint["category_id"] not in category_types:
                continue
            
            if blueprint.get("version", ""):
                product_name = blueprint["name"]+" "+blueprint["version"]
            else:
                product_name = blueprint["name"]

            if any(tag.lower() in product_name.lower() for tag in skip_tags):
                continue

            if "Secret Lair" in product_name:
                if any(tag.lower() in product_name.lower() for tag in sld_skip_tags):
                    continue

            count += 1
            sealed_data.extend([
                {
                    "name": product_name,
                    "id": blueprint["id"],
                }
            ])

        print(f"Found {count} products")

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


def load_cardmarket(secret):
    return get_cardmarket()


def mmdownload(paging):
    params = {
        "format": "json",
        "version": "V2",
        "start": str(paging["start"]),
        "rows": str(paging["rows"]),
        "variants": "true",
        "variants.count": "10",
        "fields": "*",
        "facet.multiselect": "true",
        "selectedfacet": "true",
        "pagetype": "boolean",
        "p": "categoryPath:\"Trading Card Games\"",
        "filter": [
            "categoryPath1_fq:\"Trading Card Games\"",
            "categoryPath2_fq:\"Trading Card Games>Magic the Gathering\"",
	        "stock_status_uFilter:\"In Stock\"",
            "manufacturer_uFilter:\"Wizards of the Coast\"",
        ],
    }

    r = requests.get("https://search.unbxd.io/fb500edbf5c28edfa74cc90561fe33c3/prod-miniaturemarket-com811741582229555/category", params=params)
    return json.loads(r.content)


def load_miniaturemarket(secret):
    pagination = mmdownload({"start": 0, "rows": 0})
    pages = pagination["response"]["numberOfProducts"]

    print(f"Processing {pages} pages")

    sealed_data = []

    for x in range(pages):
        products = mmdownload({"start": x, "rows": 32})

        for product in products["response"]["products"]:
            sealed_data.extend([
                {
                    # the 'title' field is full of tags like 'clearance' that we don't really need
                    "name": product.get("google_shopping_name", product["title"]),
                    "id": product["entity_id"],
                    "releaseDate": product["created_at"],
                }
            ])

    print(f"Retrieved {len(sealed_data)} products")

    return sealed_data


def scgretaildownload(guid, page):
    header = {
        "X-HawkSearch-IgnoreTracking": "true",
        "Content-Type": "application/json",
    }

    facet = {}
    facet["product_type"] = ["Sealed"]
    facet["game"] = "Magic: The Gathering"

    payload = {}
    payload["PageNo"] = page
    payload["MaxPerPage"] = 96
    payload["clientguid"] = guid
    payload["FacetSelections"] = facet

    r = requests.post("https://essearchapi-na.hawksearch.com/api/v2/search", json=payload, headers=header)
    return json.loads(r.content)


def scgbuylistdownload(bearer, offset, limit):
    header = {
        "Authorization": f"Bearer {bearer}",
        "Content-Type": "application/json",
    }

    payload = {}
    # price_category_id = 2 is sealed
    payload["filter"] = "game_id = 1 AND price_category_id = 2"
    payload["matchingStrategy"] = "all"
    payload["offset"] = offset
    payload["limit"] = limit
    payload["sort"] = ["name:asc", "set_name:asc", "finish:desc"]

    r = requests.post("https://search.starcitygames.com/indexes/sell_list_products_v2/search", json=payload, headers=header)
    return json.loads(r.content)


def load_starcity(secret):
    retail_data = load_starcity_retail(secret)
    print(f"Retrieved {len(retail_data)} products from retail")

    buylist_data = load_starcity_buylist(secret)
    print(f"Retrieved {len(buylist_data)} products from buylist")

    retail_data.extend(x for x in buylist_data if x not in retail_data)
    print(f"Total {len(retail_data)} products")

    return retail_data


def load_starcity_retail(secret):
    guid = secret.get("scg_guid")
    sealed_data = []

    numOfPages = scgretaildownload(guid, 0)["Pagination"]["NofPages"]
    for page in range(1, numOfPages + 1):
        resp = scgretaildownload(guid, page)
        for result in resp["Results"]:
            title = result["Document"]["item_display_name"][0]

            if any(tag.lower() in title.lower() for tag in ["Lorcana", "Flesh and Blood"]):
                continue

            sealed_data.extend([
                {
                    "name": title,
                    "id": result["Document"]["hawk_child_attributes"][0]["variant_sku"][0],
                }
            ])

    return sealed_data


def load_starcity_buylist(secret):
    bearer = secret.get("scg_bearer")
    sealed_data = []

    numOfElements = scgbuylistdownload(bearer, 0, 1)["estimatedTotalHits"]
    for page in range(0, numOfElements, 200):
        resp = scgbuylistdownload(bearer, page, 200)
        for result in resp["hits"]:
            title = result["name"]
            if result["subtitle"]:
                title += " " + result["subtitle"]

            if any(tag.lower() in title.lower() for tag in ["Lorcana", "Flesh and Blood"]):
                continue

            sealed_data.extend([
                {
                    "name": title,
                    "id": result["variants"][0]["sku"],
                }
            ])

    return sealed_data


def load_coolstuffinc(secret):
    skip_tags = [
        "Basic Land",
        "Bulk",
        "Card Box",
        "Complete Set (Mint/Near Mint Condition)",
        "Complete Set (Partially Sealed)",
        "CoolStuffInc.com",
        "D6 Dice",
        "Enamel Pin",
        "Factory Sealed Complete Set",
        "Grab Bag",
        "Japanese Booster",
        "Magic Rares",
        "Magic: The Gathering - New Player Deck",
        "Player's Guide",
        "Random Foil",
        "Russian Booster",
        "Set of 5 Dice",
        "Spindown Life",
        "Spinning Life Counter",
        "Token Pack",
        "Token Set",
        "Variety Pack",
    ]

    retail_data = load_coolstuffinc_retail(skip_tags)
    print(f"Retrieved {len(retail_data)} products from retail")

    try:
        buylist_data = load_coolstuffinc_buylist(skip_tags)
        print(f"Retrieved {len(buylist_data)} products from buylist")

        retail_data.extend(x for x in buylist_data if x not in retail_data)
        print(f"Total {len(retail_data)} products")
    except Exception:
        pass

    return retail_data


def load_coolstuffinc_retail(skip_tags):
    sealed_data = []

    page = 0
    while True:
        page += 1
        link = "https://www.coolstuffinc.com/sq/1556988?page=" + str(page)
        print(f"Parsing page {page}")

        header = {
            "User-Agent": "curl/8.6",
        }
        r = requests.get(link, headers=header)
        soup = BeautifulSoup(r.content, 'html.parser')

        for div in soup.find_all('div', attrs={"class": "row product-search-row main-container"}):
            try:
                title = div.find('span', attrs={"itemprop": "name"}).get_text()
                productURL = div.find('link', attrs={"itemprop": "url"}).get("content")
            except Exception:
                continue

            if any(tag.lower() in title.lower() for tag in skip_tags):
                continue

            u = urlparse(productURL)
            csiId = u.path.removeprefix("/p/")

            sealed_data.extend([
                {
                    "name": title,
                    "id": csiId,
                }
            ])

        # Exit loop condition, only when the Next field has no future links
        nextPage = soup.find('span', attrs={"id": "nextLink"})
        if not nextPage or not nextPage.find('a'):
            break

    return sealed_data


def load_coolstuffinc_buylist(skip_tags):
    sealed_data = []

    header = {
        "User-Agent": "curl/8.6",
    }
    r = requests.get("https://www.coolstuffinc.com/GeneratedFiles/SellList/Section-mtg.json", headers=header)
    buylist = json.loads(r.content)

    for product in buylist:
        if product.get("RarityName") != "Box":
            continue

        name = product.get("Name")

        if any(tag.lower() in name.lower() for tag in skip_tags):
            continue

        sealed_data.extend([
            {
                "name": name,
                "id": product.get("PID"),
            }
        ])

    return sealed_data


def get_abu_link(page):
    return "https://data.abugames.com/solr/nodes/select?facet.field=magic_edition_related&facet.field=packaging_type&facet.field=price&facet.field=language_magic_sealed_product&facet.field=condition&facet.field=promotion&facet.field=production_status&facet.field=quantity&facet.mincount=1&facet.limit=-1&facet=on&indent=on&q=*:*&fq=%2Bcategory%3A%22Magic%20the%20Gathering%20Sealed%20Product%22%20-offline_item%3Atrue%20OR%20-title%3A%22STORE%22%20OR%20-price%3A0%20%2B((%2Bquantity%3A%5B1%20TO%20*%5D)%20OR%20(%2Bquantity%3A0%20%2Balways_show_inventory%3A1))%20-magic_features%3A(%22Actual%20Picture%20Card%22)%20%2Bpackaging_type%3A((*%3A*)%20AND%20(%22Archenemy%20Deck%22%20OR%20%22Archenemy%20Deck%20Set%22%20OR%20%22Battle%20Pack%22%20OR%20%22Booster%20Box%22%20OR%20%22Booster%20Pack%22%20OR%20%22Box%20Set%22%20OR%20%22Brawl%20Deck%22%20OR%20%22Brawl%20Deck%20Set%22%20OR%20%22Challenge%20Deck%22%20OR%20%22Clash%20Pack%22%20OR%20%22Comic%20Con%20Exclusive%22%20OR%20%22Commander%20Deck%22%20OR%20%22Commander%20Deck%20Set%22%20OR%20%22Deck%20Builder%27s%20Toolkit%22%20OR%20%22Duel%20Deck%20%2F%20Global%20Series%22%20OR%20%22Event%20%2F%20Challenger%20Deck%22%20OR%20%22Event%20%2F%20Challenger%20Deck%20Set%22%20OR%20%22Fat%20Pack%20%2F%20Bundle%22%20OR%20%22From%20the%20Vault%22%20OR%20%22Gift%20Box%22%20OR%20%22Guild%20Kit%22%20OR%20%22Intro%20Pack%22%20OR%20%22Intro%20Pack%20Set%22%20OR%20%22Land%20Pack%22%20OR%20%22Planechase%20Deck%22%20OR%20%22Planechase%20Deck%20Set%22%20OR%20%22Planeswalker%20Deck%22%20OR%20%22Planeswalker%20Deck%20Set%22%20OR%20%22Prerelease%20Pack%22%20OR%20%22Prerelease%20Pack%20Set%22%20OR%20%22Promo%20%2F%20Sample%22%20OR%20%22Starter%20%2F%20Tournament%20Box%22%20OR%20%22Starter%20%2F%20Tournament%20Deck%22%20OR%20%22Starter%20Kit%22%20OR%20%22Theme%20Deck%22%20OR%20%22Theme%20Deck%20Box%22%20OR%20%22Theme%20Deck%20Set%22%20OR%20%22Themed%20Booster%20Pack%22%20OR%20%22Two-Player%20Starter%20Set%22))%20%2Bdisplay_title%3A*&sort=display_title%20asc&rows=40&wt=json&start=" + str(page * 40)


def load_abugames(nothing):
    sealed_data = []

    page = 0
    while True:
        print(f"Parsing page {page}")
        link = get_abu_link(page)

        r = requests.get(link)
        data = json.loads(r.content)
        response = data.get("response")

        if page * 40 > response.get("numFound"):
            break
        page += 1

        for product in response.get("docs"):
            product_id = product.get("id")
            name = product.get("display_title")

            if product.get("language_magic_sealed_product")[0] != "English":
                continue

            if name.endswith("(Loose)"):
                for i in range(len(sealed_data)):
                    if name.startswith(sealed_data[i].get("name")):
                        sealed_data[i]["name"] = name
                        sealed_data[i]["id"] = product_id
                        added = True
                if added:
                    continue

            sealed_data.extend([
                {
                    "name": name,
                    "id": product_id,
                }
            ])

    return sealed_data


providers_dict = {
    "cardKingdom": {
        "identifier": "cardKingdomId",
        "load_func": load_cardkingdom,
    },
    "tcgplayer": {
        "identifier": "tcgplayerProductId",
        "preload_func": preload_tcgplayer,
        "load_func": load_tcgplayer,
        "auth": ["client_id", "client_secret"],
    },
    "cardMarket": {
        "identifier": "mcmId",
        "load_func": load_cardmarket,
    },
    "cardTrader": {
        "identifier": "cardtraderId",
        "load_func": load_cardtrader,
        "auth": ["ct_token"],
    },
    "miniaturemarket": {
        "identifier": "miniaturemarketId",
        "load_func": load_miniaturemarket,
    },
    "starcitygames": {
        "identifier": "scgId",
        "load_func": load_starcity,
        "auth": ["scg_guid", "scg_bearer"],
    },
    "coolstuffinc": {
        "identifier": "csiId",
        "load_func": load_coolstuffinc,
    },
    "abugames": {
        "identifier": "abuId",
        "load_func": load_abugames,
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
        provider_ids = set()
        if ignore.get(key):
            provider_ids = set(str(x) for x in ignore[key].keys())
        ids[key] = provider_ids
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
        try:
            products = provider["load_func"](secret)
        except Exception as e:
            print(f"Could not load provider {key}")
            print(repr(e))
            products = [{
                "name": f"Could not load provider {key}",
                "id": ""
            }]

        for product in products:
            if str(product["id"]) in ids[key]:
                continue

            prod_name = product["name"]
            i = 0
            while prod_name in reviews[key]:
                i = i + 1
                prod_name = product["name"] + " " + str(i)
            reviews[key][prod_name] = {
                "identifiers": {provider["identifier"]: str(product["id"])},
                "category": "UNKNOWN",
                "subtype": "UNKNOWN"
            }
            ids[key].add(str(product["id"]))
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

    for key, provider in providers_dict.items():
        if provider.get("auth") and not all(key in secret for key in provider.get("auth")):
            print(f"{key} is disabled due missing auth")
            providers_dict[key]["disabled"] = True

    main(secret)

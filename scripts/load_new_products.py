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


def mvpdownload(session, page):
    header = {
        "Cookie": "ASP.NET_SessionId="+session,
    }

    payload = {
        'SearchKey': '',
        'PageNumber': page,
        'PageSize': 25 * page,
        'SortBy': 'MostPopular',
        'SortType': '',
        'PriceRange': '',
        'ItemStatus': 'ALL',
    }

    r = requests.post("https://go.mvpsportsandgames.com/GetSearchResults?CategoryId=62100000", data=payload, headers=header)
    return json.loads(r.content)


def load_mvp(secret):
    sealed_data = []
    page = 1
    session = secret.get("mvp_session_id")

    skip_tags = [
        "FOREIGN",
    ]

    while True:
        products = mvpdownload(session, page)
        print(f"Page {page} has {products['PageSize']} products")

        for product in products["DataList"]:
            title = product["Name"]

            if any(tag.lower() in title.lower() for tag in skip_tags):
                continue

            sealed_data.extend([
                {
                    "name": title,
                    "id": product["Id"],
                }
            ])

        # exit when we've processed all pages, or when a failover threshold is reached
        if products["PageNumber"] == products["PagesCount"] or page > 10:
            break

        page += 1


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
            subtitles = result["Document"].get("subtitle")
            if subtitles:
                title = f"{title} {subtitles[0]}"

            scgId = result["Document"]["hawk_child_attributes"][0]["variant_sku"][0]
            if not scgId.startswith("SLD-MTG"):
                continue

            sealed_data.extend([
                {
                    "name": title,
                    "id": scgId,
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

            scgId = result["variants"][0]["sku"]
            if not scgId.startswith("SLD-MTG"):
                continue

            sealed_data.extend([
                {
                    "name": title,
                    "id": scgId,
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


def get_abu_link(page, limit):
    return "https://data.abugames.com/solr/nodes/select?q=*:*&fq=%2Bcategory%3A%22Magic%20the%20Gathering%20Sealed%20Product%22%20-offline_item%3Atrue%20OR%20-title%3A%22STORE%22%20OR%20-title%3A%22AUCTION%22%20OR%20-title%3A%22OVERSTOCK%22%20%2Blanguage_magic_sealed_product%3A(%22English%22)&sort=display_title%20asc&wt=json&rows=" + str(limit) + "&start=" + str(page * limit)


def load_abugames(nothing):
    sealed_data = []

    skip_tags = [
        "VHS Video",
    ]

    page = 0
    limit = 40
    while True:
        print(f"Parsing page {page}")
        link = get_abu_link(page, limit)

        header = {
            "User-Agent": "curl/8.6",
        }
        r = requests.get(link, headers=header)
        data = json.loads(r.content)
        response = data.get("response")

        if len(response.get("docs")) == 0:
            break
        page += 1

        for product in response.get("docs"):
            product_id = product.get("id")
            name = product.get("display_title")

            if product.get("language_magic_sealed_product")[0] != "English":
                continue

            if name.endswith("(Loose)"):
                added = False
                for i in range(len(sealed_data)):
                    if name.startswith(sealed_data[i].get("name")):
                        sealed_data[i]["name"] = name
                        sealed_data[i]["id"] = product_id
                        added = True
                if added:
                    continue

            if any(tag.lower() in name.lower() for tag in skip_tags):
                continue

            # some older products have outdated conditions
            if product.get("condition") != "NM":
                continue

            sealed_data.extend([
                {
                    "name": name,
                    "id": product_id,
                }
            ])

    return sealed_data


def load_tnt(nothing):
    sealed_data = []

    skip_tags = [
        "Omega Collector",
        "Silver Stamped",
        "- Promo",
        " | Clue Token",
        "Italian",
        "Spanish",
        "Portuguese",
        "German",
        "French",
        "Chinese",
    ]

    page = 0
    while True:
        page += 1
        link = "https://www.trollandtoad.com/magic-the-gathering/magic-the-gathering-sealed-product/909?page-no=" + str(page)
        print(f"Parsing page {page}")

        header = {
            "User-Agent": "curl/8.6",
        }
        r = requests.get(link, headers=header)
        soup = BeautifulSoup(r.content, 'html.parser')

        for div in soup.find_all('div', attrs={"class": "product-info card-body col pl-0 pl-sm-3"}):
            try:
                name = div.find('div', attrs={"class": "col-11 prod-title"}).get_text().strip()
                productURL = div.find('a', attrs={"class": "card-text"}).get("href")
                print(f"Found {title} {productURL}")
            except Exception:
                continue

            if any(tag.lower() in name.lower() for tag in skip_tags):
                continue

            tntId = productURL.rsplit('/', 1)[-1]
            print(f"Found {title} {tntId}")

            sealed_data.extend([
                {
                    "name": name,
                    "id": tntId,
                }
            ])

        # Exit loop condition, only when the Next field has no future links
        nextPage = soup.find('div', attrs={"class": "pageText px-1 d-none d-md-block"})
        if not nextPage:
            break

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
    "trollandtoad": {
        "identifier": "tntId",
        "load_func": load_tnt,
    },
    "mvpsportsandgames": {
        "identifier": "mvpId",
        "load_func": load_mvp,
        "auth": ["mvp_session_id"],
    },
}


def main(secret, pull_data=True):
    if pull_data:
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
        if len(sys.argv) > 1 and sys.argv[1] == "--parseonly":
            main({}, False)
            quit()
        pass

    for key, provider in providers_dict.items():
        if provider.get("auth") and not all(key in secret for key in provider.get("auth")):
            print(f"{key} is disabled due missing auth")
            providers_dict[key]["disabled"] = True

    main(secret)

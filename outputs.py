import yaml
import json
import ijson
from tqdm import tqdm
from pathlib import Path
import logging
import logging.handlers as handlers
import os
import itertools as itr
from copy import copy
import collections.abc

def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = recursive_update(d.get(k, {}), v)
        else:
            d[k] = v
    return d

def get_uuid_sealed(product):
    filename = product["set"].upper()
    if filename == "CON":
        filename = "CON_"
    filename += ".json"
    file = Path("mtgJson/AllSetFiles").joinpath(filename)
    with open(file, "r") as jfile:
        objects = list(ijson.items(jfile, "data.sealedProduct.item"))
        for o in objects:
            if o["name"] == product["name"]:
                return o["uuid"]
    raise KeyError(f"Missing UUID for {product['name']}")

def get_uuid_card(card):
    filename = card["set"].upper()
    if filename == "CON":
        filename = "CON_"
    filename += ".json"
    file = Path("mtgJson/AllSetFiles").joinpath(filename)
    with open(file, "r") as jfile:
        objects = list(ijson.items(jfile, "data.cards.item"))
        for o in objects:
            if o["number"] == str(card["number"]):
                return o["uuid"]
    raise KeyError(f"Missing UUID for {card['name']}")

def validate_contents(contents, route, logger):
    if not contents:
        logger.error("%s missing contents %s", route, contents)
        return False
    if not isinstance(contents, dict):
        logger.error("%s has invalid contents format", route)
        return False
    for key, value in contents.items():
        if key == "sealed":
            try:
                if not value:
                    logger.warning("%s sealed is empty", route)
                for product in value:
                    ptemp = copy(product)
                    if not isinstance(ptemp.pop("set"), str):
                        raise TypeError("set is not string")
                    if not isinstance(ptemp.pop("count"), int):
                        raise TypeError("count is not int")
                    if not isinstance(ptemp.pop("name"), str):
                        raise TypeError("name is not str")
                    if ptemp:
                        logger.warning("%s sealed has extra contents %s", route, str(ptemp))
                    try:
                        product["uuid"] = get_uuid_sealed(product)
                    except KeyError:
                        logger.warning("Could not get UUID for sealed %s/%s", route, product["name"])
            except KeyError as e:
                logger.error("%s sealed missing required value %s", route, e)
                return False
            except TypeError as e:
                logger.error("%s sealed has incorrect value type: %s", route, e)
                return False
        elif key == "pack":
            if "card_count" not in contents:
                logger.info("%s pack missing card count", route)
            try:
                if not value:
                    logger.warning("%s pack is empty", route)
                for product in value:
                    ptemp = copy(product)
                    if not isinstance(ptemp.pop("set"), str):
                        raise TypeError("set is not string")
                    if not isinstance(ptemp.pop("code"), str):
                        raise TypeError("code is not string")
                    if ptemp:
                        logger.warning("%s pack has extra contents %s", route, str(ptemp))
            except KeyError as e:
                logger.error("%s pack missing required value %s", route, e)
                return False
            except TypeError as e:
                logger.error("%s pack has incorrect value type: %s", route, e)
                return False
        elif key == "deck":
            if "card_count" not in contents:
                logger.info("%s deck missing card count", route)
            try:
                if not value:
                    logger.warning("%s deck is empty", route)
                for product in value:
                    ptemp = copy(product)
                    if not isinstance(ptemp.pop("set"), str):
                        raise TypeError("set is not string")
                    if not isinstance(ptemp.pop("name"), str):
                        raise TypeError("name is not string")
                    if ptemp:
                        logger.warning("%s deck has extra contents %s", route, str(ptemp))
            except KeyError as e:
                logger.error("%s deck missing required value %s", route, e)
                return False
        elif key == "other":
            try:
                if not value:
                    logger.warning("%s other is empty", route)
                for product in value:
                    ptemp = copy(product)
                    if not isinstance(ptemp.pop("name"), str):
                        raise TypeError("name is not string")
                    if ptemp:
                        logger.warning("%s other has extra contents %s", route, str(ptemp))
            except KeyError as e:
                logger.error("%s other missing required value %s", route, e)
                return False
            except TypeError as e:
                logger.error("%s other has incorrect value type: %s", route, e)
                return False
        elif key == "card":
            try:
                if not value:
                    logger.warning("%s pack is empty", route)
                for product in value:
                    ptemp = copy(product)
                    if not isinstance(ptemp.pop("set"), str):
                        raise TypeError("set is not string")
                    number = ptemp.pop("number")
                    if not (isinstance(number, int) or isinstance(number, str)):
                        raise TypeError("number is not int or string")
                    if not isinstance(ptemp.pop("name"), str):
                        raise TypeError("name is not string")
                    if not isinstance(ptemp.pop("foil"), bool):
                        raise TypeError("foil is not boolean")
                    if ptemp:
                        logger.warning("%s pack has extra contents %s", route, str(ptemp))
                    try:
                        product["uuid"] = get_uuid_card(product)
                    except KeyError:
                        logger.warning("Could not get UUID for card %s/%s", route, product["name"])
            except KeyError as e:
                logger.error("%s pack missing required value %s", route, e)
                return False
            except TypeError as e:
                logger.error("%s pack has incorrect value type: %s", route, e)
                return False
        elif key == "card_count":
            if not isinstance(value, int):
                logger.error("%s card count is not integer value", route)
                return False
        elif key == "variable":
            check = True
            try:
                for configuration in value:
                    if "card_count" in contents:
                        check *= validate_contents(dict({"card_count": contents["card_count"]}, **configuration), route+"-variable", logger)
                    else:
                        check *= validate_contents(configuration, route+"-variable", logger)
            except:
                logger.error("%s variable formatted incorrectly", route)
                return False
            if not check:
                return False
        else:
            logger.error("%s key %s not recognized", route, key)
            return False
    return True

def iterative_sum(list_of_dicts, logger=None):
    all_keys = set().union(*[set(k.keys()) for k in list_of_dicts])
    if "variable" in all_keys:
        list_of_dicts = [parse_variable(d) for d in list_of_dicts]
    if logger:
        logger.info(str(list_of_dicts))
        logger.info(str(all_keys))
    temp_return = {}
    for k in all_keys:
        for d in list_of_dicts:
            if k in d:
                if k not in temp_return:
                    temp_return[k] = copy(d[k])
                else:
                    temp_return[k] += d[k]
    return temp_return

def parse_variable(contents, logger=None):
    if "variable_mode" not in contents:
        return contents
    options = contents.pop("variable_mode")
    temp_variable = []
    if logger:
        logger.info(str(contents))
    if options.get("replacement", False):
        for combo in itr.combinations_with_replacement(contents["variable"], options.get("count", 1)):
            temp_variable.append(iterative_sum(combo, logger))
    else:
        for combo in itr.combinations(contents["variable"], options.get("count", 1)):
            temp_variable.append(iterative_sum(combo, logger))
    contents["variable"] = temp_variable
    return contents
    
def deck_links(contents, uuid, logger=None):
    link = {}
    for d in contents.get("deck", []):
        if d["set"] not in link:
            link[d["set"]] = {}
        if d["name"] not in link[d["set"]]:
            link[d["set"]][d["name"]] = set()
        link[d["set"]][d["name"]].add(uuid)
    for v in contents.get("variable", []):
        link = recursive_update(link, deck_links(v, uuid, logger))
    return link

logfile_name = "output.log"
logger = logging.getLogger()
logger.setLevel(logging.INFO)
rollCheck = os.path.isfile(logfile_name)
handler = handlers.RotatingFileHandler(logfile_name, backupCount=5, encoding="utf-8")
formatter = logging.Formatter("%(levelname)s - %(message)s")

handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

if rollCheck:
    logger.handlers[0].doRollover()

contents_files = Path("data/contents/").glob("*.yaml")
new_files = Path("data/products").glob("*.yaml")

products_contents = {}
deck_mapper = {}

for file in contents_files:
    with open(file, "rb") as f:
        data = yaml.safe_load(f)
    if not data["products"]:
        logger.error("Set %s has no products", data["code"])
        os.remove(file)
    for product, contents in data["products"].items():
        if "variable" in contents:
            contents = parse_variable(contents)
        if validate_contents(contents, data["code"] + "-" + product, logger):
            if data["code"] not in products_contents:
                products_contents[data["code"]] = {}
            try:
                self_uuid = get_uuid_sealed({"set": data["code"], "name": product})
                deck_mapper = recursive_update(deck_mapper, deck_links(contents, self_uuid, logger))
            except KeyError:
                logger.warning("Could not get UUID for sealed %s/%s", data["code"], product)
            products_contents[data["code"]][product] = contents

with open("outputs/contents.json", "w") as outfile:
    json.dump(products_contents, outfile)

for set_code in deck_mapper.keys():
    for deck in deck_mapper[set_code].keys():
        deck_mapper[set_code][deck] = list(deck_mapper[set_code][deck])

with open("outputs/deck_map.json", "w") as outfile:
    json.dump(deck_mapper, outfile)

products_new = {}

for file in new_files:
    with open(file, "rb") as f:
        data = yaml.safe_load(f)
    products_new[data["code"]] = data["products"]

with open("outputs/products.json", "w") as outfile:
    json.dump(products_new, outfile)

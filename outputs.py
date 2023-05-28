import yaml
import json
import ijson
from tqdm import tqdm
from pathlib import Path
import logging
import logging.handlers as handlers
import os
from copy import copy

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

for file in contents_files:
	with open(file, "rb") as f:
		data = yaml.safe_load(f)
	for product, contents in data["products"].items():
		if validate_contents(contents, data["code"] + "-" + product, logger):
			if data["code"] not in products_contents:
				products_contents[data["code"]] = {}
			products_contents[data["code"]][product] = contents

with open("outputs/contents.json", "w") as outfile:
	json.dump(products_contents, outfile)

products_new = {}

for file in new_files:
	with open(file, "rb") as f:
		data = yaml.safe_load(f)
	products_new[data["code"]] = data["products"]

with open("outputs/products.json", "w") as outfile:
	json.dump(products_new, outfile)

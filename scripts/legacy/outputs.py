import argparse
import pathlib

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

import card_to_product_compiler
import generate_original_printing_details


def recursive_update(d, u):
    for k, v in u.items():
        if isinstance(v, collections.abc.Mapping):
            d[k] = recursive_update(d.get(k, {}), v)
        elif isinstance(v, set):
            d[k] = d.get(k, set()).union(v)
        else:
            d[k] = v
    return d


def build_uuid_map():
    file = Path("mtgJson/AllPrintings.json")
    file.parent.mkdir(parents=True, exist_ok=True)

    uuids = {}
    with open(file, "rb") as jfile:
        parser = ijson.parse(jfile)
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


def validate_contents(contents, route, logger, uuid_map, cc=True):
    if not contents:
        logger.info("%s missing contents %s", route, contents)
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
                    ptemp.pop("uuid", False)
                    if ptemp:
                        logger.warning(
                            "%s sealed has extra contents %s", route, str(ptemp)
                        )
                    try:
                        product["uuid"] = uuid_map[product["set"]]["sealedProduct"][
                            product["name"]
                        ]
                    except KeyError:
                        logger.warning(
                            "Could not get UUID for sealed %s/%s",
                            route,
                            product["name"],
                        )
            except KeyError as e:
                logger.error("%s sealed missing required value %s", route, e)
                return False
            except TypeError as e:
                logger.error("%s sealed has incorrect value type: %s", route, e)
                return False
        elif key == "pack":
            if cc and "card_count" not in contents:
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
                        logger.warning(
                            "%s pack has extra contents %s", route, str(ptemp)
                        )
                    if product["code"] not in uuid_map[product["set"]]["booster"]:
                        logger.warning(
                            "%s-%s pack not present in MTGJson data",
                            route,
                            product["code"],
                        )
            except KeyError as e:
                logger.error("%s pack missing required value %s", route, e)
                return False
            except TypeError as e:
                logger.error("%s pack has incorrect value type: %s", route, e)
                return False
        elif key == "deck":
            if cc and "card_count" not in contents:
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
                        logger.warning(
                            "%s deck has extra contents %s", route, str(ptemp)
                        )
                    if product["name"] not in uuid_map[product["set"]]["decks"]:
                        logger.warning(
                            "%s-%s deck not present in MTGJson data",
                            route,
                            product["name"],
                        )
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
                        logger.warning(
                            "%s other has extra contents %s", route, str(ptemp)
                        )
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
                    if not isinstance(ptemp.pop("foil", False), bool):
                        raise TypeError("foil is not boolean")
                    if ptemp:
                        logger.warning(
                            "%s pack has extra contents %s", route, str(ptemp)
                        )
                    try:
                        if not product.get("foil", False):
                            product.pop("foil", False)
                        product["number"] = str(product["number"])
                        product["uuid"] = uuid_map[product["set"]]["cards"][
                            str(product["number"])
                        ]
                    except KeyError:
                        logger.warning(
                            "Could not get UUID for card %s/%s", route, product["name"]
                        )
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
                for product in value:
                    for configuration in product["configs"]:
                        check *= validate_contents(
                            configuration,
                            route + "-variable",
                            logger,
                            uuid_map,
                            cc=False,
                        )
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
        for combo in itr.combinations_with_replacement(
            contents["variable"], options.get("count", 1)
        ):
            temp_variable.append(iterative_sum(combo, logger))
    else:
        for combo in itr.combinations(contents["variable"], options.get("count", 1)):
            temp_variable.append(iterative_sum(combo, logger))
    contents["variable"] = [{"configs": temp_variable}]
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


if __name__ == "__main__":
    logfile_name = "logs/output.log"
    pathlib.Path(logfile_name).parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    rollCheck = os.path.isfile(logfile_name)
    handler = handlers.RotatingFileHandler(
        logfile_name, backupCount=5, encoding="utf-8"
    )
    formatter = logging.Formatter("%(levelname)s - %(message)s")

    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    logger.addHandler(handler)

    if rollCheck:
        logger.handlers[0].doRollover()

    contents_files = list(Path("data/contents/").glob("*.yaml"))
    new_files = list(Path("data/products").glob("*.yaml"))

    products_contents = {}
    deck_mapper = {}
    uuid_map = build_uuid_map()

    for file in tqdm(contents_files, position=0):
        with open(file, "rb") as f:
            data = yaml.safe_load(f)
        if not data["products"]:
            logger.error("Set %s has no products", data["code"])
            os.remove(file)
        for product, contents in tqdm(
            data["products"].items(), position=1, leave=False
        ):
            if "copy" in contents:
                contents = data["products"][contents["copy"]]
            if "variable" in contents:
                contents = parse_variable(contents)
            if validate_contents(
                contents, data["code"] + "-" + product, logger, uuid_map
            ):
                if data["code"] not in products_contents:
                    products_contents[data["code"]] = {}
                try:
                    self_uuid = uuid_map[data["code"]]["sealedProduct"][product]
                    deck_mapper = recursive_update(
                        deck_mapper, deck_links(contents, self_uuid, logger)
                    )
                except KeyError:
                    logger.warning(
                        "Could not get UUID for sealed %s/%s", data["code"], product
                    )
                products_contents[data["code"]][product] = contents

    with open("outputs/contents.json", "w") as outfile:
        json.dump(products_contents, outfile)

    for set_code in deck_mapper.keys():
        for deck in deck_mapper[set_code].keys():
            deck_mapper[set_code][deck] = list(deck_mapper[set_code][deck])

    with open("outputs/deck_map.json", "w") as outfile:
        json.dump(deck_mapper, outfile)

    products_new = {}

    for file in tqdm(new_files):
        with open(file, "rb") as f:
            data = yaml.safe_load(f)
        products_new[data["code"]] = data["products"]

    with open("outputs/products.json", "w") as outfile:
        json.dump(products_new, outfile)

    card_to_product_compiler.populate_temporary_enhanced_all_printings(
        argparse.Namespace(
            input_file="mtgJson/AllPrintings.json", output_file="outputs/card_map.json"
        )
    )

    generate_original_printing_details.populate_temporary_enhanced_all_printings()

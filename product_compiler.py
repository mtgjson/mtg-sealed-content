import ijson
from tqdm import tqdm
import yaml
from pathlib import Path
import logging
import logging.handlers as handlers
import os
import os.path as path
import time
import requests

logfile_name = "logs/product.log"
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
logger.info("Starting logging")

jsonFile = "mtgJson/AllPrintings.json"
if path.getmtime(jsonFile) < time.time() - 24*60*60:
    url = "https://mtgjson.com/api/v5/AllPrintings.json"
    r = requests.get(url)
    open(jsonFile, 'wb').write(r.content)
    logger.info("Downloaded new MTGJson content")


alt_codes = {
    "con_": "con"
}
r_alt_codes = {
    "CON": "CON_"
}

total = 0
complete = 0

codes = set()
with open(jsonFile, 'rb') as allPrintings:
    all_sets = dict(ijson.kvitems(allPrintings, "data"))
    for set_code, contents in tqdm(all_sets.items()):
        output_file = Path("data/contents/").joinpath(r_alt_codes.get(set_code, set_code).upper()).with_suffix(".yaml")
        if output_file.is_file():
            with open(output_file, 'r') as f:
                full = yaml.safe_load(f)
            try:
                empties = {k for k, v in full["products"].items() if not v}
                products = {k: v for k, v in full["products"].items() if v}
            except:
                empties = set()
                products = full
        else:
            empties = set()
            products = {}
        if "sealedProduct" not in contents:
            continue
        sealed_product = list(contents["sealedProduct"])
        mtgjson_names = [p["name"] for p in sealed_product]
        existing_names = [k for k in products.keys()]
        total += len(mtgjson_names)
        complete += len(existing_names)
        for p in sealed_product:
            if p["name"] not in products:
                if p["name"] not in empties:
                    logger.info("Added new product %s/%s", set_code, p["name"])
                products[p["name"]] = []
        for n in existing_names:
            if n not in mtgjson_names:
                logger.info("Product %s/%s no longer present in MTGJson data", set_code, n)
        if products:
            with open(output_file, 'w') as write:
                yaml.dump({"code": set_code.lower(), "products": products}, write)


logger.info("%s out of %s products complete", complete, total)


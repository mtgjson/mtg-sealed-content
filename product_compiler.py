import ijson
from tqdm import tqdm
import yaml
from pathlib import Path
import logging
import logging.handlers as handlers
import os

logfile_name = "product.log"
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

alt_codes = {
    "con_": "con"
}

logger.info("Starting logging")
total = 0
complete = 0

parentPath = Path("mtgJson/AllSetfiles/")
files = list(parentPath.glob("*.json"))
t = tqdm(files)
codes = set()
for file in t:
    output_file = Path("data/contents/").joinpath(file.with_suffix(".yaml").name)
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
    with open(file, 'rb') as ifile:
        sealed_product = list(ijson.items(ifile, "data.sealedProduct.item"))
        mtgjson_names = [p["name"] for p in sealed_product]
        existing_names = [k for k in products.keys()]
        total += len(mtgjson_names)
        complete += len(existing_names)
        for p in sealed_product:
            if p["name"] not in products:
                if p["name"] not in empties:
                    logger.info("Added new product %s/%s", file.stem, p["name"])
                products[p["name"]] = []
        for n in existing_names:
            if n not in mtgjson_names:
                logger.info("Product %s/%s no longer present in MTGJson data", file.stem, n)
    code = alt_codes.get(file.stem.lower(), file.stem.lower())
    if products:
        with open(output_file, 'w') as write:
            yaml.dump({"code": code, "products": products}, write)
t.close
del(t)

logger.info("%s out of %s products complete", complete, total)


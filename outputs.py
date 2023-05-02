import yaml
import json
from tqdm import tqdm
from pathlib import Path
import logging
import logging.handlers as handlers
import os

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
valid_contents = ["sealed", "pack", "deck", "other", "variable", "card_count", "card"]

for file in contents_files:
	with open(file, "rb") as f:
		data = yaml.safe_load(f)
	for product, contents in data["products"].items():
		if contents:
			if data["code"] not in products_contents:
				products_contents[data["code"]] = {}
			if ("pack" in contents or "deck" in contents) and "card_count" not in contents:
			    logger.info("%s/%s missing card count", data["code"], product)
			if any([c not in valid_contents for c in contents.keys()]):
			    logger.error("%s/%s has invalid content codes", data["code"], product)
			else:
			    products_contents[data["code"]][product] = contents
		else:
			logger.info("%s/%s missing contents", data["code"], product)

with open("outputs/contents.json", "w") as outfile:
	json.dump(products_contents, outfile)

products_new = {}

for file in new_files:
	with open(file, "rb") as f:
		data = yaml.safe_load(f)
	products_new[data["code"]] = data["products"]

with open("outputs/products.json", "w") as outfile:
	json.dump(products_new, outfile)

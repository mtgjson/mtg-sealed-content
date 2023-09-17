import pathlib

import ijson
import yaml
from pathlib import Path
import os
import os.path as path
import time
import requests


def main():
    url = "https://mtgjson.com/api/v5/AllPrintings.json"
    r = requests.get(url, stream=True)

    alt_codes = {"con_": "con"}
    r_alt_codes = {"CON": "CON_"}

    total = 0
    complete = 0

    codes = set()
    all_sets = dict(ijson.kvitems(r.content, "data"))
    for set_code, contents in all_sets.items():
        output_file = (
            Path("data/contents/")
            .joinpath(r_alt_codes.get(set_code, set_code).upper())
            .with_suffix(".yaml")
        )
        if output_file.is_file():
            with open(output_file, "r") as f:
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
                    with open("status.txt", 'a') as f:
                        f.write(f"Added new product {set_code}/{p['name']}\n")
                products[p["name"]] = []
        for n in existing_names:
            if n not in mtgjson_names:
                with open("status.txt", 'a') as f:
                    f.write(f"Product {set_code}/{p['name']} no longer present\n")
        if products:
            with open(output_file, "w") as write:
                yaml.dump({"code": set_code.lower(), "products": products}, write)


if __name__ == "__main__":
    main()

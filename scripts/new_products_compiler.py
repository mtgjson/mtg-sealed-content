import yaml
import json
from pathlib import Path


def main(new_contents):
    products_new = {}
    for file in sorted(new_contents.glob("*.yaml")):
        with open(file, "rb") as f:
            data = yaml.safe_load(f)
        products_new[data["code"]] = data["products"]

    with open("outputs/products.json", "w") as outfile:
        json.dump(products_new, outfile)


if __name__ == "__main__":
    main(Path("data/products"))

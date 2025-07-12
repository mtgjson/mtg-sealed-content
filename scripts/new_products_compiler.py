import yaml
import json
from pathlib import Path


def main(new_contents):
    products_new = {}
    for file in sorted(new_contents.glob("*.yaml")):
        with open(file, "rb") as f:
            data = yaml.safe_load(f)

        for p_name, p_info in data["products"].items():
            if (p_info["subtype"] in ["SECRET_LAIR", "SECRET_LAIR_BUNDLE"]) and "release_date" not in p_info:
                with open("status.txt", 'a') as status_file:
                    status_file.write(f"Product {file.stem} - {p_name} missing required release date\n")
        products_new[data["code"]] = data["products"]

    with open("outputs/products.json", "w") as outfile:
        json.dump(products_new, outfile)


if __name__ == "__main__":
    main(Path("data/products"))

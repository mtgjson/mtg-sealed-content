import yaml
import product_classes as pc
from pathlib import Path
import json

if __name__ == "__main__":
    contentFolder = Path("data/contents/")
    failed = False
    for set_file in contentFolder.glob("*.yaml"):
        with open(set_file, 'rb') as f:
            contents = yaml.safe_load(f)

        for name, p in contents["products"].items():
            try:
                pc.product(p)
            except:
                print(f"Product {name} in set {set_file.stem} failed")
                failed = True
    if failed:
        raise ImportError()
    print("All products validated")

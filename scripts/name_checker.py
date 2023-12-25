import yaml
from pathlib import Path

if __name__ == "__main__":
    productsFolder = Path("data/products/")
    failed = False
    all_files = sorted(list(productsFolder.glob("*.yaml")))
    all_products = {}
    for set_file in all_files:
        with open(set_file, "rb") as f:
            contents = yaml.safe_load(f)
        set_code = contents['code']
        for name, p in contents["products"].items():
            if p["category"] not in all_products:
                all_products[p["category"]] = {}
            if p["subtype"] not in all_products[p["category"]]:
                all_products[p["category"]][p["subtype"]] = []
            all_products[p["category"]][p["subtype"]].append(f"{set_code}-{name}")
    for category, c_products in all_products.items():
        print(category)
        for subtype, s_products in c_products.items():
            print(f"  {subtype}")
            for product in s_products:
                print(f"    {product}")

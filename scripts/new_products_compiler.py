if __package__:
    from .atomic_write import atomic_write
    from . import sealed_yaml
else:
    from atomic_write import atomic_write
    import sealed_yaml

import json

date_required_subtypes = ["SECRET_LAIR", "SECRET_LAIR_BUNDLE"]

def main():
    products_new = {}
    for stem, data in sealed_yaml.iter_sets():
        # outputs/products.json carries the definitions only, in either layout
        products = {
            p_name: {key: value for key, value in p_info.items() if key != "contents"}
            for p_name, p_info in data["products"].items()
        }
        for p_name, p_info in products.items():
            if (p_info["subtype"] in date_required_subtypes) and "release_date" not in p_info:
                with open("status.txt", 'a') as status_file:
                    status_file.write(f"Product {stem} - {p_name} missing required release date\n")
        products_new[data["code"]] = products

    # Sorted keys keep the output byte-stable whatever key order the YAML uses
    with atomic_write('outputs/products.json') as outfile:
        json.dump(products_new, outfile, sort_keys=True)


if __name__ == "__main__":
    main()

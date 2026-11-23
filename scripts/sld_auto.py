if __package__:
    from . import sealed_yaml
else:
    import sealed_yaml

from thefuzz import fuzz
import ijson
import requests
import sys

def main():
    url = r"https://mtgjson.com/api/v5/SLD.json"
    r = requests.get(url, stream=True, timeout=(10, 60))
    r.raise_for_status()
    uuids = {}
    parser = ijson.parse(r.content)

    decks = []

    for prefix, event, value in parser:
        if prefix == "data.decks.item.name" and event == "string":
            decks.append({"name": value})

    sld_products = sealed_yaml.load_set("SLD")

    product_names = list(sld_products["products"].keys())
    mapped_decks = {}
    for k, v in sld_products["products"].items():
        for dk in (v.get("contents") or {}).get("deck", []):
            mapped_decks[dk["name"]] = k
    index = 0
    offset = 0
    while index < len(decks):
        deck = decks[index]
        index += 1

        if deck["name"] in mapped_decks:
            continue

        print(f"Finding similar products for {deck['name']}")
        product_names.sort(key=lambda x: fuzz.token_sort_ratio(x, deck["name"]), reverse=True)
        for i in range(5):
            print(f"  {i} - {product_names[i + offset]}")
    
        try:
            product_check = input("Select action ('h' for help): ")
        except EOFError:
            sys.exit(1)
    
        # Look for the product name itself
        for i in range(len(product_names)):
            if product_check.strip().lower() == product_names[i].lower():
                product_check = "0"
                offset = i

        if product_check == "q":
            break
        elif product_check == "s":
            offset = 0
            continue
        elif product_check == "m":
            index -= 1
            offset += 5
            if offset + 5 > len(product_names):
                offset = 0
        elif product_check == "u":
            index -= 2
            if index < 0:
                print("NOTE: There is no product before this one")
                index = 0
            offset = 0
        elif product_check in "01234":
            if product_check == "":
                product_check = "0"

            check_index = int(product_check) + offset
            p_name = product_names[check_index]
            contents = sld_products["products"][p_name].setdefault("contents", {})
            if "deck" not in contents:
                contents["deck"] = [{"name": deck["name"], "set": "sld"}]

            # Only flag an unknown bonus when nothing describes one yet: an existing
            # note such as "Drop has no bonus card slot" is research, not a gap
            if not {"card", "pack", "variable", "other"} & set(contents):
                contents["other"] = [{"name": "Bonus card unknown"}]

            print(contents)
        else:
            index -= 1
            if product_check != "h":
                print(f"Invalid action: {product_check}")
            print("Available actions: q - quit / s - skip / m - more / u - undo / [0]124 - pick / use the exact name of the product")

        if product_check not in "mb":
            offset = 0

    sealed_yaml.save_set("SLD", sld_products)


if __name__ == "__main__":
    main()

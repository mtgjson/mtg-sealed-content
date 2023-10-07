import json


def recursive_compare(new_data, old_data, route=""):
    if isinstance(new_data, dict):
        if not isinstance(old_data, dict):
            raise TypeError(f"{route} - Incompatible types")
        for k in new_data.keys():
            if k not in old_data:
                raise IndexError(f"{route} - Key {k} not in old data")
            recursive_compare(new_data[k], old_data[k], route + " " + k)
    elif isinstance(new_data, list):
        if not isinstance(old_data, list):
            raise TypeError(f"{route} - Incompatible types")
        for k in range(len(new_data)):
            found = False
            for o_value in old_data:
                try:
                    recursive_compare(new_data[k], o_value, route + " " + str(k))
                except:
                    continue
                else:
                    found = True
            if not found:
                raise IndexError(f"{route} - object {new_data[k]} not in old data")
    elif type(new_data) != type(old_data):
        raise TypeError(f"{route} - Incompatible types")
    else:
        if new_data != old_data:
            raise IndexError(f"{route} - Mismatched elements")


with open("outputs/contents.json", "rb") as new:
    new_data = json.load(new)

with open("/Users/samzimmerman/Downloads/contents.json", "rb") as old:
    old_data = json.load(old)

recursive_compare(new_data, old_data)

with open("outputs/deck_map.json", "rb") as new:
    new_data = json.load(new)

with open("/Users/samzimmerman/Downloads/deck_map.json", "rb") as old:
    old_data = json.load(old)

recursive_compare(new_data, old_data)

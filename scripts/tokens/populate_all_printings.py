"""
This is a helper script that can be used to identify what token(s) might be missing from the
MTGJSON data set and can be either corrected for within code or manually overwritten in the
data/token_manual_overrides.json file.

Make sure the working directory is Repo Root (probably "mtg-sealed-content")
"""

import json
import pathlib

from .all_printings import AllPrintings

ENHANCED_ALL_PRINTINGS_PATH = pathlib.Path(
    "outputs/AllPrintings_withTokenParts_temporary.json"
)
MISSING_TXT_PATH = pathlib.Path("outputs/missing_tokenParts.txt")


def populate_temporary_enhanced_all_printings():
    all_printings = AllPrintings()

    data = all_printings.get_data()
    for set_code, set_data in data.get("data").items():
        code_to_use = (
            set_code if "parentCode" not in set_data else set_data["parentCode"]
        )

        token_struct_path = pathlib.Path(
            f"outputs/token_products_mappings/{code_to_use}.json"
        )
        if not token_struct_path.exists():
            print(f"Skipping {set_code} ({code_to_use})")
            continue

        with token_struct_path.open("r") as fp:
            token_data_mapping = json.load(fp)

        print(f"Working on {set_code} ({code_to_use})")
        for index, token_details in enumerate(set_data.get("tokens", [])):
            if token_details["uuid"] in token_data_mapping:
                set_data["tokens"][index]["tokenProducts"] = token_data_mapping[
                    token_details["uuid"]
                ]

    with ENHANCED_ALL_PRINTINGS_PATH.open("w") as fp:
        json.dump(data, fp, indent=4, ensure_ascii=False, sort_keys=True)


def populate_missing_txt():
    with ENHANCED_ALL_PRINTINGS_PATH.open("r") as fp:
        data = json.load(fp)

    with MISSING_TXT_PATH.open("w") as fp:
        found = 0
        missing = 0
        for set_code, set_data in data.get("data").items():
            parent_set_code = set_data.get("parentCode", set_data.get("code"))
            for index, token_details in enumerate(set_data.get("tokens", [])):
                if "tokenProducts" in token_details:
                    found += 1
                    continue
                # UUID, Parent Set Code, Set Code, Name, Number, Side
                fp.write(
                    f"{token_details['uuid']}, {parent_set_code}, {set_code}, \"{token_details['name']}\", {token_details['number']}, {token_details.get('side', 'NO_SIDE')}\n"
                )
                missing += 1
        fp.write(
            f"\nFound {found}/{found + missing} ({found / (found + missing) * 100}%) tokens"
        )


if __name__ == "__main__":
    populate_temporary_enhanced_all_printings()
    populate_missing_txt()

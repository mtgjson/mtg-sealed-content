import json
import pathlib

from scripts.tokens.all_printings import AllPrintings


def main():
    all_printings = AllPrintings()

    data = all_printings.get_data()
    for set_code, set_data in data.get("data").items():
        code_to_use = (
            set_code if "parentCode" not in set_data else set_data["parentCode"]
        )

        token_struct_path = pathlib.Path(
            f"/Users/zach/Desktop/Development/mtg-sealed-content/outputs/token_products_mappings/{code_to_use}.json"
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

    with pathlib.Path("/Users/zach/Desktop/AllPrintings_withTokenParts.json").open(
        "w"
    ) as fp:
        json.dump(data, fp, indent=4, ensure_ascii=False, sort_keys=True)


def main2():
    with pathlib.Path("/Users/zach/Desktop/AllPrintings_withTokenParts.json").open(
        "r"
    ) as fp:
        data = json.load(fp)

    with pathlib.Path("/Users/zach/Desktop/missing.txt").open("w") as fp:
        for set_code, set_data in data.get("data").items():
            # if set_code != "AZNR":
            #     continue
            for index, token_details in enumerate(set_data.get("tokens", [])):
                if "tokenProducts" in token_details:
                    continue
                print(f"Unable to find tokenProducts for {token_details}")
                fp.write(
                    f"Missing tokenProducts {set_code} - {token_details['name']} ({token_details['number']}-{token_details.get('side', 'NO_SIDE')})\n"
                )


if __name__ == "__main__":
    main()
    main2()

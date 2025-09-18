import json
import lzma
import pathlib
import tempfile
from typing import Dict

import requests


def download_and_save_mtgjson_all_printings(save_path: pathlib.Path) -> None:
    file_bytes = b""
    file_data = requests.get(
        "https://mtgjson.com/api/v5/AllPrintings.json.xz", stream=True, timeout=60
    )
    for chunk in file_data.iter_content(chunk_size=1024 * 36):
        if chunk:
            file_bytes += chunk

    with save_path.open("w", encoding="utf8") as f:
        f.write(lzma.decompress(file_bytes).decode())


def load_prior_scryfall_to_mtgjson_uuid_mapping(
    load_path: pathlib.Path,
) -> Dict[str, Dict[str, str]]:
    if not load_path.exists():
        return {}

    with load_path.open("r", encoding="utf8") as fp:
        return json.load(fp)


def generate_scryfall_to_mtgjson_uuid_mapping(
    all_printings_path: pathlib.Path, prior_mapping: Dict[str, Dict[str, str]]
) -> Dict[str, Dict[str, str]]:
    with all_printings_path.open("r", encoding="utf8") as fp:
        all_printings_data = json.load(fp)

    sf_to_mtgjson_mapping = prior_mapping

    for set_code, set_data in all_printings_data.get("data", {}).items():
        for mtgjson_card in set_data.get("cards", []):
            scryfall_id = mtgjson_card.get("identifiers", {}).get("scryfallId")
            if not scryfall_id:
                continue

            if scryfall_id not in sf_to_mtgjson_mapping:
                sf_to_mtgjson_mapping[scryfall_id] = {}

            mtgjson_card_side = mtgjson_card.get("side", "a")
            if mtgjson_card_side in sf_to_mtgjson_mapping[scryfall_id]:
                # We don't want to overwrite a side if it already exists, so we skip it
                continue

            sf_to_mtgjson_mapping[scryfall_id][mtgjson_card_side] = mtgjson_card["uuid"]
            sf_to_mtgjson_mapping[scryfall_id]["_name"] = mtgjson_card["name"]

    return sf_to_mtgjson_mapping


def save_scryfall_to_mtgjson_uuid_mapping(
    new_mapping: Dict[str, Dict[str, str]], save_path: pathlib.Path
) -> None:
    with save_path.open("w", encoding="utf8") as fp:
        json.dump(new_mapping, fp, indent=4, sort_keys=True)


def main():
    temporary_all_printings = tempfile.NamedTemporaryFile(delete=False)
    temporary_all_printings_path = pathlib.Path(temporary_all_printings.name)

    download_and_save_mtgjson_all_printings(temporary_all_printings_path)

    scryfall_to_mtgjson_uuid_dump_path = pathlib.Path(
        "outputs/scryfall_to_mtgjson_uuid_mapping.json"
    )

    prior_mapping_data = load_prior_scryfall_to_mtgjson_uuid_mapping(
        scryfall_to_mtgjson_uuid_dump_path
    )
    new_mapping_data = generate_scryfall_to_mtgjson_uuid_mapping(
        temporary_all_printings_path, prior_mapping_data
    )

    save_scryfall_to_mtgjson_uuid_mapping(
        new_mapping_data, scryfall_to_mtgjson_uuid_dump_path
    )

    temporary_all_printings_path.unlink()


if __name__ == "__main__":
    main()

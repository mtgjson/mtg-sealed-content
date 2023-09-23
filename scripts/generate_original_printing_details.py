import json
import multiprocessing
import pathlib
from collections import ChainMap

from gatherer_provider import GathererProvider, MtgjsonForeignDataObject, LANGUAGE_MAP
from scryfall_provider import ScryfallProvider

output_file = pathlib.Path("./outputs/gatherer_mapping.json").absolute()


def get_prior_output():
    if not output_file.is_file():
        return {}

    with output_file.open(encoding="utf-8") as fp:
        prior_results = json.load(fp)

    return prior_results


def write_outputs(output):
    if not output_file.is_file():
        output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8") as fp:
        json.dump(
            {int(k): v for k, v in output.items()},
            fp,
            sort_keys=True,
            ensure_ascii=False,
            default=lambda o: o.to_json(),
        )


def get_mid_contents(card):
    multiverse_ids = card.get("multiverse_ids", [])
    set_code = card.get("set", "").upper()

    if not multiverse_ids:
        return {}

    gatherer_id_to_struct = {}
    gatherer_provider = GathererProvider()
    for multiverse_id in multiverse_ids:
        gatherer_id_to_struct[str(multiverse_id)] = gatherer_provider.get_cards(
            multiverse_id, set_code
        )
        print(f"{set_code} - {card.get('name')} - {multiverse_id}")

    foreign_id_to_structs = parse_foreign(
        card["prints_search_uri"].replace("%22", ""),
        card["name"],
        card["collector_number"],
        set_code.lower(),
    )
    gatherer_id_to_struct.update(foreign_id_to_structs)

    return gatherer_id_to_struct


def divide_chunks(iterable, size):
    for i in range(0, len(iterable), size):
        yield iterable[i : i + size]


def parse_foreign(sf_prints_url: str, card_name: str, card_number: str, set_name: str):
    card_foreign_entries = {}

    # Add information to get all languages
    sf_prints_url = sf_prints_url.replace("&unique=prints", "+lang%3Aany&unique=prints")

    prints_api_json = ScryfallProvider().download_all_pages(sf_prints_url)
    if not prints_api_json:
        print(f"No data found for {sf_prints_url}: {prints_api_json}")
        return []

    for foreign_card in prints_api_json:
        if (
            set_name != foreign_card["set"]
            or card_number != foreign_card["collector_number"]
            or foreign_card["lang"] == "en"
        ):
            continue

        card_foreign_entry = MtgjsonForeignDataObject("", None, None, None, None, None)
        try:
            card_foreign_entry.language = LANGUAGE_MAP[foreign_card["lang"]]
        except IndexError:
            print(f"Unable to get language {foreign_card}")

        if foreign_card["multiverse_ids"]:
            foreign_card_multiverse_id = str(foreign_card["multiverse_ids"][0])
        else:
            continue

        if "card_faces" in foreign_card:
            if card_name.lower() == foreign_card["name"].split("/")[0].strip().lower():
                face = 0
            else:
                face = 1

            card_foreign_entry.name = " // ".join(
                [
                    face_data.get("printed_name", face_data.get("name", ""))
                    for face_data in foreign_card["card_faces"]
                ]
            )

            foreign_card = foreign_card["card_faces"][face]
            card_foreign_entry.face_name = foreign_card.get("printed_name")
            if not card_foreign_entry.face_name:
                card_foreign_entry.face_name = foreign_card.get("name")

        if not card_foreign_entry.name:
            card_foreign_entry.name = foreign_card.get("printed_name")

            # https://github.com/mtgjson/mtgjson/issues/611
            if set_name.upper() == "IKO" and card_foreign_entry.language == "Japanese":
                card_foreign_entry.name = str(card_foreign_entry.name).split(
                    " //", maxsplit=1
                )[0]

        card_foreign_entry.text = foreign_card.get("printed_text")
        card_foreign_entry.flavor_text = foreign_card.get("flavor_text")
        card_foreign_entry.type = foreign_card.get("printed_type_line")

        if card_foreign_entry.name:
            print(
                f"{set_name.upper()} - {card_name} - {card_foreign_entry.name} - {card_foreign_entry.language} - {foreign_card_multiverse_id}"
            )
            card_foreign_entries[foreign_card_multiverse_id] = [card_foreign_entry]

    return card_foreign_entries


def main():
    gatherer_id_to_struct = get_prior_output()
    scryfall_provider = ScryfallProvider()

    set_codes = scryfall_provider.get_all_scryfall_sets()
    for set_code in set_codes:
        cards = scryfall_provider.download_cards(set_code)
        if not cards:
            continue

        top_card_multiverse_ids = cards[0].get("multiverse_ids", [])
        if (
            not top_card_multiverse_ids
            or str(top_card_multiverse_ids[0]) in gatherer_id_to_struct
        ):
            continue

        for card_chunk in divide_chunks(cards, 10):
            with multiprocessing.Pool() as pool:
                results = pool.map(get_mid_contents, card_chunk)
            gatherer_id_to_struct.update(ChainMap(*results))

        write_outputs(gatherer_id_to_struct)


if __name__ == "__main__":
    main()

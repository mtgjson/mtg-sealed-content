from typing import List, Optional
import bs4
import datetime
import json
import re
import html
import multiprocessing
import pathlib
import requests_cache


class GathererDownloader:
    session: requests_cache.CachedSession
    original_text_regex: re.Pattern
    multiverse_id_text_regex: re.Pattern
    adventure_text_regex: re.Pattern
    old_school_mana_regex: re.Pattern

    def __init__(self, session: requests_cache.CachedSession) -> None:
        self.session = session
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:141.0) Gecko/20100101 Firefox/141.0"
            }
        )

        self.original_text_regex = re.compile(r"\"instanceText\":\"(.*?)\",")
        self.multiverse_id_text_regex = re.compile(r'\\"multiverseId\\":([0-9]+)')
        self.adventure_text_regex = re.compile(r"\n?//ADV//\n(?:.*?\n){3}(.*)")
        self.old_school_mana_regex = re.compile(r"o?o([0-9]+|[WUBRGX])")

    def __del__(self) -> None:
        self.session.close()

    def get_set_codes(self) -> List[str]:
        url = "https://gatherer.wizards.com/sets?page={0}"

        set_codes = []

        for page_number in range(1, 25):
            formatted_url = url.format(page_number)
            paged_response = self.session.get(formatted_url)

            soup = bs4.BeautifulSoup(paged_response.text, "html.parser")

            at_least_one_set_found = False
            for a_tag in soup.find_all("a"):
                card_url = a_tag.get("href")
                if card_url and card_url.startswith(f"/sets/"):
                    at_least_one_set_found = True
                    set_codes.append(card_url.split("/sets/")[-1])

            if not at_least_one_set_found:
                break

        return set_codes

    def get_card_urls_from_set_code(self, set_code: str) -> List[str]:
        url = "https://gatherer.wizards.com/sets/{0}?page={1}"

        card_urls = []

        for page_number in range(1, 100):
            formatted_url = url.format(set_code, page_number)
            paged_response = self.session.get(formatted_url)

            soup = bs4.BeautifulSoup(paged_response.content, "html.parser")

            at_least_one_card_found = False
            for a_tag in soup.find_all("a"):
                card_url = a_tag.get("href")
                if card_url and card_url.startswith(f"/{set_code}/en-us"):
                    at_least_one_card_found = True
                    card_urls.append(f"https://gatherer.wizards.com{card_url}")

            if not at_least_one_card_found:
                break

        return card_urls

    def get_card_multiverse_id(self, card_url: str) -> Optional[int]:
        card_data_response = self.session.get(card_url).content.decode("utf-8")
        multiverse_ids = self.multiverse_id_text_regex.findall(card_data_response)
        if multiverse_ids:
            return int(multiverse_ids[0])
        raise Exception(f"No multiverse ID found for {card_url}\n{card_data_response}")

    def get_card_original_printed_text(self, card_url: str) -> Optional[str]:
        card_data_response = html.unescape(
            self.session.get(card_url)
            .content.decode("unicode_escape")
            .replace("\u2028", "")  # Annoying exception case
            .encode("latin1")
            .decode("utf-8")
        )

        original_texts = self.original_text_regex.findall(card_data_response)
        if not original_texts:
            return ""

        text = original_texts[0]
        functions = [
            self.__strip_slashes,
            self.__strip_adventure_component,
            self.__fix_old_school_mana,
            self.__strip_html,
        ]
        for func in functions:
            text = func(text)
        return text

    @staticmethod
    def __strip_slashes(card_text: str) -> str:
        return card_text.replace("\\n", "\n").replace('\\"', '"')

    def __strip_adventure_component(self, card_text: str) -> str:
        if "//ADV//" not in card_text:
            return card_text

        adventure_texts = self.adventure_text_regex.findall(card_text)
        return adventure_texts[0]

    def __fix_old_school_mana(self, card_text: str) -> str:
        return self.old_school_mana_regex.sub(r"{\1}", card_text)

    @staticmethod
    def __strip_html(card_text: str) -> str:
        if "<" not in card_text:
            return card_text

        return bs4.BeautifulSoup(card_text, "html.parser").get_text()


def download_set(set_code: str) -> None:
    print("Downloading {0}".format(set_code))
    cached_session = requests_cache.CachedSession(
        cache_name=f"caches/gatherer_cache_{set_code}",
        expire_after=datetime.timedelta(days=100),
        stale_if_error=True,
    )
    downloader = GathererDownloader(cached_session)

    multiverse_id_to_printed_text_mapping = dict()

    card_urls = downloader.get_card_urls_from_set_code(set_code)
    for card_url in card_urls:
        multiverse_id = downloader.get_card_multiverse_id(card_url)
        original_printed_text = downloader.get_card_original_printed_text(card_url)
        multiverse_id_to_printed_text_mapping[multiverse_id] = original_printed_text

    with pathlib.Path(f"dumps/{set_code}.json").open("w") as dump_file:
        json.dump(
            multiverse_id_to_printed_text_mapping,
            dump_file,
            indent=4,
            sort_keys=True,
            ensure_ascii=False,
        )


def get_set_codes():
    cached_session = requests_cache.CachedSession(
        cache_name=f"caches/gatherer_cache_main",
        expire_after=datetime.timedelta(days=100),
        stale_if_error=True,
    )
    try:
        downloader = GathererDownloader(cached_session)
        return sorted(downloader.get_set_codes())
    finally:
        cached_session.close()


def main():
    pathlib.Path("caches").mkdir(parents=True, exist_ok=True)
    pathlib.Path("dumps").mkdir(parents=True, exist_ok=True)

    set_codes = get_set_codes()

    # Download all set data in parallel
    with multiprocessing.Pool() as pool:
        pool.map(download_set, set_codes)

    combined_multiverse_id_to_printed_text_mappings = {}

    # Load and merge each JSON file from 'dumps' into the combined dictionary
    for done_set_path in pathlib.Path("dumps").glob("*.json"):
        with done_set_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
            combined_multiverse_id_to_printed_text_mappings.update(data)

    # Convert all keys to integers (they are strings in the JSON dumps)
    final_result = {
        int(key): value
        for key, value in combined_multiverse_id_to_printed_text_mappings.items()
    }
    with pathlib.Path("outputs/gatherer_mapping.json").open(
        "w", encoding="utf-8"
    ) as out:
        json.dump(final_result, out, indent=4, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    main()

import re
import sys
import time
from typing import Any, Dict, List, Optional, Union

import ratelimit
import requests.exceptions

from retryable_session import retryable_session


class ScryfallProvider:
    ALL_SETS_URL: str = "https://api.scryfall.com/sets/"
    CARDS_URL_ALL_DETAIL_BY_SET_CODE: str = "https://api.scryfall.com/cards/search?include_extras=true&include_variations=true&order=set&q=e%3A{}&unique=prints"

    def download_all_pages(
        self,
        starting_url: Optional[str],
        params: Optional[Dict[str, Union[str, int]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Connects to Scryfall API and goes through all redirects to get the
        card data from their several pages via multiple API calls
        :param starting_url: First Page URL
        :param params: Params to pass to Scryfall API
        """
        all_cards: List[Dict[str, Any]] = []

        page_downloaded = 1
        starting_url = f"{starting_url}&page={page_downloaded}"

        while starting_url:
            page_downloaded += 1

            response: Dict[str, Any] = self.download(starting_url, params)
            if response["object"] == "error":
                if response["code"] != "not_found":
                    print(f"Unable to download {starting_url}: {response}")
                break

            data_response: List[Dict[str, Any]] = response.get("data", [])
            all_cards.extend(data_response)

            # Go to the next page, if it exists
            if not response.get("has_more"):
                break

            starting_url = re.sub(
                r"&page=\d+", f"&page={page_downloaded}", starting_url, count=1
            )

        return all_cards

    @ratelimit.sleep_and_retry
    @ratelimit.limits(calls=40, period=1)
    def download(
        self,
        url: str,
        params: Optional[Dict[str, Union[str, int]]] = None,
        retry_ttl: int = 3,
    ) -> Any:
        """
        Download content from Scryfall
        Api calls always return JSON from Scryfall
        :param url: URL to download from
        :param params: Options for URL download
        :param retry_ttl: How many times to retry if Chunk Error
        """
        session = retryable_session()

        try:
            response = session.get(url)
        except requests.exceptions.ChunkedEncodingError as error:
            if retry_ttl:
                print(f"Download failed: {error}... Retrying")
                time.sleep(3 - retry_ttl)
                return self.download(url, params, retry_ttl - 1)

            print(f"Download failed: {error}... Maxed out retries")
            sys.exit(1)

        try:
            return response.json()
        except ValueError as error:
            if "504" in response.text:
                print("Scryfall 504 error, sleeping...")
            else:
                print(
                    f"Unable to convert response to JSON for URL: {url} -> {error}; Message = {response.text}"
                )

            time.sleep(5)
            return self.download(url, params)

    def download_cards(self, set_code: str) -> List[Dict[str, Any]]:
        """
        Get all cards from Scryfall API for a particular set code
        :param set_code: Set to download (Ex: AER, M19)
        :return: List of all card objects
        """
        print(f"Downloading {set_code} cards")
        scryfall_cards = self.download_all_pages(
            self.CARDS_URL_ALL_DETAIL_BY_SET_CODE.format(set_code)
        )

        # Return sorted by card name, and by card number if the same name is found
        return sorted(
            scryfall_cards, key=lambda card: (card["name"], card["collector_number"])
        )

    def get_all_scryfall_sets(self) -> List[str]:
        """
        Grab all sets that Scryfall currently supports
        :return: Scryfall sets
        """
        scryfall_sets = self.download(self.ALL_SETS_URL)

        if scryfall_sets["object"] == "error":
            print(f"Downloading Scryfall data failed: {scryfall_sets}")
            return []

        # Get _ALL_ Scryfall sets
        scryfall_set_codes = [
            set_obj["code"].upper() for set_obj in scryfall_sets["data"]
        ]

        # Remove Scryfall token sets (but leave extra sets)
        scryfall_set_codes = [
            set_code
            for set_code in scryfall_set_codes
            if not (set_code.startswith("t") and set_code[1:] in scryfall_set_codes)
        ]

        return sorted(scryfall_set_codes)

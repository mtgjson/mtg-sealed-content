import copy
import dataclasses
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Union

import bs4
import ratelimit
import requests
import urllib3.exceptions

from retryable_session import retryable_session


@dataclass
class GathererCard:
    card_name: str
    original_types: str
    original_text: Optional[str]
    flavor_text: Optional[str]

    def to_json(self):
        return dataclasses.asdict(
            self, dict_factory=lambda x: {k: v for (k, v) in x if v is not None}
        )


@dataclass
class MtgjsonForeignDataObject:
    language: str
    face_name: Optional[str]
    flavor_text: Optional[str]
    name: Optional[str]
    text: Optional[str]
    type: Optional[str]

    def to_json(self):
        return dataclasses.asdict(
            self, dict_factory=lambda x: {k: v for (k, v) in x if v is not None}
        )


SYMBOL_MAP: Dict[str, str] = {
    "White": "W",
    "Blue": "U",
    "Black": "B",
    "Red": "R",
    "Green": "G",
    "Colorless": "C",
    "Variable Colorless": "X",
    "Snow": "S",
    "Energy": "E",
    "Phyrexian White": "PW",
    "Phyrexian Blue": "PU",
    "Phyrexian Black": "PB",
    "Phyrexian Red": "PR",
    "Phyrexian Green": "PG",
    "Two or White": "2W",
    "Two or Blue": "2U",
    "Two or Black": "2B",
    "Two or Red": "2R",
    "Two or Green": "2G",
    "White or Blue": "WU",
    "White or Black": "WB",
    "Blue or Black": "UB",
    "Blue or Red": "UR",
    "Black or Red": "BR",
    "Black or Green": "BG",
    "Red or Green": "RG",
    "Red or White": "GU",
    "Green or White": "RW",
    "Green or Blue": "GW",
    "Half a White": "HW",
    "Half a Blue": "HU",
    "Half a Black": "HB",
    "Half a Red": "HR",
    "Half a Green": "HG",
    "Tap": "T",
    "Untap": "Q",
    "Infinite": "∞",
}

LANGUAGE_MAP: Dict[str, str] = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese (Brazil)",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "zhs": "Chinese Simplified",
    "zht": "Chinese Traditional",
    "he": "Hebrew",
    "la": "Latin",
    "grc": "Ancient Greek",
    "ar": "Arabic",
    "sa": "Sanskrit",
    "ph": "Phyrexian",
    "px": "Phyrexian",
}


class GathererProvider:
    GATHERER_CARD = "https://gatherer.wizards.com/Pages/Card/Details.aspx"
    SET_CHECKLIST_URL = "https://gatherer.wizards.com/Pages/Search/Default.aspx?page={}&output=checklist&set=[%22{}%22]"
    SETS_TO_REMOVE_PARENTHESES = {"10E"}

    @ratelimit.limits(calls=40, period=1)
    def download(
        self, url: str, params: Optional[Dict[str, Union[str, int]]] = None
    ) -> Optional[requests.Response]:
        """
        Download a file from gather, with a rate limit
        :param url: URL to download
        :param params: URL parameters
        :return URL response
        """
        session = retryable_session(retries=3)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        try:
            response = session.get(url, params=params, verify=False)
        except (
            urllib3.exceptions.MaxRetryError,
            requests.exceptions.RetryError,
            requests.exceptions.SSLError,
            requests.exceptions.ConnectionError,
        ) as exception:
            print(f"Unable to get {url} with {params}: {exception}")
            return None

        if response.status_code != 200:
            print(f"Unable to download {url} with {params}: {response.status_code}")
            return None

        return response

    def get_collector_number_to_multiverse_id_mapping(
        self, set_name: str
    ) -> Dict[str, str]:
        """
        Generate a mapping between card collector numbers and their MultiverseId number for
        backup processing, if our other providers are lacking this data
        :param set_name: Set name, as Gatherer doesn't like set codes
        :returns Mapping of collector number to Multiverse ID
        """
        card_number_to_multiverse_id = {}

        for page_number in range(0, 10):
            response = self.download(
                self.SET_CHECKLIST_URL.format(page_number, set_name)
            )

            if not response:
                continue

            soup = bs4.BeautifulSoup(response.text, "html.parser")

            checklist_tables = soup.find("table", class_="checklist")
            if not checklist_tables:
                break

            cards = checklist_tables.find_all("tr", class_="cardItem")
            for card in cards:
                row_card_number = card.find("td", class_="number").text
                row_card_multiverse_id = (
                    card.find("td", class_="name")
                    .find("a")
                    .get("href", "")
                    .split("=", 2)[-1]
                )

                card_number_to_multiverse_id[row_card_number] = row_card_multiverse_id

            last_paging_value = soup.find("div", class_="pagingcontrols").find_all("a")
            if not last_paging_value:
                break
            last_paging_value = last_paging_value[-1]

            is_last_page = (
                "underline" in last_paging_value.get("style", "")
                or ">" not in last_paging_value.text
            )
            if is_last_page:
                break

        return card_number_to_multiverse_id

    def get_cards(self, multiverse_id: str, set_code: str = "") -> List[GathererCard]:
        """
        Get card(s) matching a given multiverseId
        :param multiverse_id: Multiverse ID of the card
        :param set_code: Set code to find the card in
        :return All found cards matching description
        """

        response = self.download(
            self.GATHERER_CARD, {"multiverseid": multiverse_id, "printed": "true"}
        )

        if not response:
            return []

        return self.parse_cards(
            response.text, set_code in self.SETS_TO_REMOVE_PARENTHESES
        )

    def parse_cards(
        self, gatherer_data: str, strip_parentheses: bool = False
    ) -> List[GathererCard]:
        """
        Parse all cards from a given gatherer page
        :param gatherer_data: Data from gatherer response
        :param strip_parentheses: Should strip details
        :return All found cards, parsed
        """
        soup = bs4.BeautifulSoup(gatherer_data, "html.parser")
        columns = soup.find_all("td", class_="rightCol")
        return [self._parse_column(c, strip_parentheses) for c in columns]

    def _parse_column(
        self, gatherer_column: bs4.element.Tag, strip_parentheses: bool
    ) -> GathererCard:
        """
        Parse a single gatherer page 'rightCol' entry
        :param gatherer_column: Column from BeautifulSoup's Gatherer parse
        :param strip_parentheses: Should additional strip occur
        :return Magic card details
        """
        label_to_values = {
            row.find("div", class_="label")
            .getText(strip=True)
            .rstrip(":"): row.find("div", class_="value")
            for row in gatherer_column.find_all("div", class_="row")
        }

        card_name = label_to_values["Card Name"].getText(strip=True)
        card_types = label_to_values["Types"].getText(strip=True)

        flavor_lines = []
        if "Flavor Text" in label_to_values:
            for flavor_box in label_to_values["Flavor Text"].find_all(
                "div", class_="flavortextbox"
            ):
                flavor_lines.append(flavor_box.getText(strip=True))

        original_text_lines = []
        if "Card Text" in label_to_values:
            for textbox in label_to_values["Card Text"].find_all(
                "div", class_="cardtextbox"
            ):
                textbox_value = self._replace_symbols(textbox).getText().strip()

                # Introduce line breaks when necessary, as Gatherer doesn't provide this all the time
                textbox_line = textbox_value.replace(card_name, "(CN)")
                textbox_line = re.sub(
                    r"([^ ({\"\-−+/>A-Z])([A-Z])", r"\1\n\2", textbox_line
                )
                textbox_line = textbox_line.replace("(CN)", card_name)

                original_text_lines.extend(textbox_line.split("\n"))

        original_text: Optional[str] = "\n".join(original_text_lines).strip() or None
        if strip_parentheses and original_text:
            original_text = self.strip_parentheses_from_text(original_text)

        return GathererCard(
            card_name=card_name,
            original_types=card_types,
            original_text=re.sub(r"<[^>]+>", "", original_text)
            if original_text
            else None,
            flavor_text="\n".join(flavor_lines).strip() or None,
        )

    @staticmethod
    def _replace_symbols(tag: bs4.BeautifulSoup) -> bs4.BeautifulSoup:
        """
        Replace all image tags with their mapped symbol
        :param tag: BS4 data tag
        :return BS4 data tag with updated symbols
        """
        tag_copy = copy.copy(tag)
        images = tag_copy.find_all("img")
        for image in images:
            alt = image["alt"]
            symbol = SYMBOL_MAP.get(alt, alt)
            image.replace_with("{" + symbol + "}")
        return tag_copy

    @staticmethod
    def strip_parentheses_from_text(text: str) -> str:
        """
        Remove all text within parentheses from a card, along with
        extra spaces.
        :param text: Text to modify
        :return: Stripped text
        """
        return re.sub(r" \([^)]*\)", "", text).replace("  ", " ").strip()

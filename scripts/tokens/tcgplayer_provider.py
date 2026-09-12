import itertools
import json
import multiprocessing
import os
import pathlib
import tempfile
from typing import Dict, Any, Iterable, List

import requests

from ..retryable_session import retryable_session


class TcgplayerProvider:
    __session: requests.Session

    def __init__(self) -> None:
        self.__session = retryable_session()
        self.__session.headers.update(
            {"Authorization": f"Bearer {self.__get_tcgplayer_auth_token()}"}
        )

    @staticmethod
    def __get_tcgplayer_auth_token():
        tcg_post = retryable_session().post(
            "https://api.tcgplayer.com/token",
            data={
                "grant_type": "client_credentials",
                "client_id": os.environ.get("TCGPLAYER_CLIENT_ID"),
                "client_secret": os.environ.get("TCGPLAYER_CLIENT_SECRET"),
            },
            timeout=60,
        )

        if not tcg_post.ok:
            raise Exception(f"Unable to contact TCGPlayer. Reason: {tcg_post.reason}")

        try:
            request_as_json = json.loads(tcg_post.text)
        except json.decoder.JSONDecodeError as exception:
            raise Exception(
                f"Unable to decode TCGPlayer API Response {tcg_post.text}"
            ) from exception

        try:
            return str(request_as_json["access_token"])
        except KeyError as exception:
            raise Exception(
                f"Unable to decode TCGPlayer API Response {tcg_post.text}"
            ) from exception

    def download(self, url: str, params: Dict[str, Any]):
        cache_path = pathlib.Path(
            f"caches/tcgplayer/{params['groupId']}-{params['offset']}.json"
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists():
            try:
                with cache_path.open("r") as fp:
                    cached = json.load(fp)
                # Older runs cached [] for both valid empty pages and API
                # failures. Re-fetch those rather than trusting an ambiguous
                # pagination terminator. Corrupt caches also need a refresh.
                if isinstance(cached, list) and cached and all(
                    isinstance(item, dict) for item in cached
                ):
                    return cached
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        print(f"Downloading {url} with params {params}")
        with self.__session.get(url, params=params) as response:
            response.raise_for_status()
            payload = response.json()

        # Fail closed: an API error or malformed envelope is not an empty page.
        # See https://docs.tcgplayer.com/reference/catalog_getproducts-1
        if not isinstance(payload, dict) or payload.get("success") is not True:
            raise ValueError("TCGplayer catalog response did not report success")
        if payload.get("errors"):
            raise ValueError("TCGplayer catalog response reported errors")
        results = payload.get("results")
        if not isinstance(results, list) or not all(
            isinstance(item, dict) for item in results
        ):
            raise ValueError("TCGplayer catalog response must contain a results list of objects")

        # Publish a complete cache file only after validation and serialization.
        # A failed refresh leaves the previous cache untouched.
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=cache_path.parent,
                prefix=f".{cache_path.name}.", suffix=".tmp", delete=False,
            ) as fp:
                temporary_path = pathlib.Path(fp.name)
                json.dump(results, fp, indent=4, ensure_ascii=False, sort_keys=True)
            temporary_path.replace(cache_path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return results

    def download_exhaustive(
        self,
        url: str,
        params: Dict[str, Any],
        api_offset: int = 0,
        offsets_per_thread: int = 100,
        threads: int = 10,
    ) -> List[Dict[str, Any]]:
        max_api_offset = api_offset + threads * offsets_per_thread

        args = [
            (url, {**params, "offset": offset})
            for offset in range(api_offset, max_api_offset, offsets_per_thread)
        ]

        with multiprocessing.Pool(processes=threads) as pool:
            starmap_results = pool.starmap(self.download, args)

        results = list(itertools.chain.from_iterable(starmap_results))
        if not results:
            return []

        return results + self.download_exhaustive(url, params, max_api_offset)

    def get_tokens_from_group_ids(
        self, group_ids: Iterable[int]
    ) -> List[Dict[str, Any]]:
        cards_and_tokens = []
        for group_id in group_ids:
            cards_and_tokens += self.get_tokens_from_group_id(group_id)

        tokens = []
        for card_or_token in cards_and_tokens:
            for data_entry in card_or_token.get("extendedData", {}):
                if self.__entry_is_token(card_or_token["name"], data_entry):
                    tokens.append(card_or_token)
                    break

        return tokens

    def get_tokens_from_group_id(self, group_id: int) -> List[Dict[str, Any]]:
        return self.download_exhaustive(
            "https://api.tcgplayer.com/catalog/products",
            {
                "categoryId": 1,
                "groupId": group_id,
                "productTypes": "Cards",
                "getExtendedFields": True,
                "limit": 100,
            },
        )

    @staticmethod
    def __entry_is_token(card_name: str, data_entry: Dict[str, Any]) -> bool:
        """
        TCGPlayer tokens have a lot of words in their name that indicate they're a token and
        not a card. Those words include "token" and "art", but the full exhaustive list is annotated
        below within code. Tokens can also have a variety of rarities, because of course they can.
        :param card_name: Card (or Token) name to check
        :param data_entry: Enhanced data entry from TCGPlayer to check
        :return: Is the card_name provided a token?
        """
        valid_token_name_parts = [
            "token",
            "art",
            "theme",
            "bio",
            "decklist",
            "emblem",
            "punch",
            "helper",
            "minigame",
        ]
        # Some tokens are labeled as 'S'pecial vs 'T'oken vs 'P'romo.
        valid_token_rarities = ["S", "T", "P"]

        if any([part in card_name.lower() for part in valid_token_name_parts]):
            return (
                data_entry["name"] == "Rarity"
                and data_entry["value"] in valid_token_rarities
            )

        return False

import itertools
import json
import multiprocessing
import os
from typing import Dict, Any, Iterable, List

import pathlib
import requests

from scripts.retryable_session import retryable_session


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
        print(f"Downloading {url} with params {params}")

        response = self.__session.get(url, params=params)
        response_decoded = response.content.decode()

        try:
            response = json.loads(response_decoded)
            return list(response.get("results", []))
        except json.decoder.JSONDecodeError:
            return []

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
                if self.__entry_is_token(data_entry):
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
    def __entry_is_token(data_entry: Dict[str, Any]) -> bool:
        # Some tokens are labeled as 'P'romo vs 'T'oken
        return data_entry["name"] == "Rarity" and data_entry["value"] in ["P", "T"]

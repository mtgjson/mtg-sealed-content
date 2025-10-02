import json
import lzma
import pathlib
import tempfile
from collections import defaultdict
from typing import Dict, Any, Set, List

from scripts.retryable_session import retryable_session


class AllPrintings:
    __temp_file: pathlib.Path
    __temp_file_data: Any

    def __init__(self) -> None:
        self.__temp_file = self.__download_all_printings()
        self.__temp_file_data = self.__read_all_printings()

    def __del__(self) -> None:
        self.__temp_file.unlink()

    @staticmethod
    def __download_all_printings() -> pathlib.Path:
        file_bytes = b""
        file_data = retryable_session().get(
            "https://mtgjson.com/api/v5/AllPrintings.json.xz", stream=True, timeout=60
        )
        for chunk in file_data.iter_content(chunk_size=1024 * 36):
            if chunk:
                file_bytes += chunk

        save_location = tempfile.NamedTemporaryFile(delete=False, delete_on_close=False)
        save_location_pathlib = pathlib.Path(save_location.name)

        with save_location_pathlib.open("w", encoding="utf8") as f:
            f.write(lzma.decompress(file_bytes).decode())

        return save_location_pathlib

    def __read_all_printings(self) -> Dict[str, Any]:
        with self.__temp_file.open("r", encoding="utf8") as f:
            return json.load(f)

    def create_mapping_mtgjson_set_code_to_tcgplayer_group_ids(
        self,
    ) -> Dict[str, Set[int]]:
        set_code_to_tcgplayer_group_ids = defaultdict(set)

        for set_code, set_data in self.__temp_file_data.get("data").items():
            if "tcgplayerGroupId" not in set_data:
                continue

            mapping_key = set_data.get("parentCode") or set_data.get("code")
            if not mapping_key:
                continue

            set_code_to_tcgplayer_group_ids[mapping_key].add(
                set_data.get("tcgplayerGroupId")
            )

        return set_code_to_tcgplayer_group_ids

    def create_mapping_mtgjson_parent_set_code_to_children_set_codes(
        self,
    ) -> Dict[str, Set[str]]:
        parent_code_to_children_set_codes = defaultdict(set)

        for set_code, set_data in self.__temp_file_data.get("data").items():
            if "parentCode" not in set_data:
                continue

            parent_code_to_children_set_codes[set_data.get("parentCode")].add(set_code)

        return parent_code_to_children_set_codes

    def get_tokens_from_set_code(self, set_code: str) -> List[Dict[str, Any]]:
        set_data = self.__temp_file_data.get("data").get(set_code)
        return set_data.get("tokens", [])

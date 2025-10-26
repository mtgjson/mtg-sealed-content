import io
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
        # self.__temp_file.unlink()
        pass

    @staticmethod
    def __download_all_printings() -> pathlib.Path:
        return pathlib.Path("/Users/zach/Downloads/AllPrintings.json")

        buffer = io.BytesIO()
        response = retryable_session().get(
            "https://mtgjson.com/api/v5/AllPrintings.json.xz", stream=True, timeout=60
        )

        for chunk in response.iter_content(chunk_size=1024 * 36):
            if chunk:
                buffer.write(chunk)

        buffer.seek(0)
        decompressed_data = lzma.decompress(buffer.read()).decode("utf-8")

        save_location = tempfile.NamedTemporaryFile(delete=False, delete_on_close=False)
        save_location_path = pathlib.Path(save_location.name)

        with save_location_path.open("w", encoding="utf8") as f:
            f.write(decompressed_data)

        return save_location_path

    def __read_all_printings(self) -> Dict[str, Any]:
        with self.__temp_file.open("r", encoding="utf8") as f:
            return json.load(f)

    def create_mapping_mtgjson_set_code_to_tcgplayer_group_ids(
        self,
    ) -> Dict[str, Set[int]]:
        set_code_to_tcgplayer_group_ids = defaultdict(set)

        for set_code, set_data in self.__temp_file_data.get("data").items():
            if "tcgplayerGroupId" not in set_data:
                print(f"No tcgplayerGroupId found for {set_code}")
                continue

            mapping_key = set_data.get("parentCode") or set_data.get("code")
            if not mapping_key:
                print(
                    "No parentCode or code found for ",
                    set_code,
                )
                continue

            set_code_to_tcgplayer_group_ids[mapping_key].add(
                set_data.get("tcgplayerGroupId")
            )
            print(
                f"set_code_to_tcgplayer_group_ids[{mapping_key}].add({set_data.get('tcgplayerGroupId')}) for {set_code}"
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

    def get_data(self) -> Dict[str, Any]:
        return self.__temp_file_data

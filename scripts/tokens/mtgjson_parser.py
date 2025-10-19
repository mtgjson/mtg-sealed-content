from typing import Dict, Set, OrderedDict, List, Any

from scripts.tokens.all_printings import AllPrintings


class MtgjsonParser:
    __all_printings: AllPrintings
    __set_code_to_group_ids: Dict[str, Set[int]]
    __set_code_to_children_set_codes: Dict[str, Set[str]]

    def __init__(self) -> None:
        self.__all_printings = AllPrintings()

        self.__set_code_to_group_ids = (
            self.__all_printings.create_mapping_mtgjson_set_code_to_tcgplayer_group_ids()
        )
        self.__set_code_to_children_set_codes = (
            self.__all_printings.create_mapping_mtgjson_parent_set_code_to_children_set_codes()
        )

        # Manual overrides because TCGplayer is lacking :(
        self.__set_code_to_group_ids["30A"].add(17666)
        # self.__set_code_to_group_ids["GK1"].add(2290)

    def get_associated_mtgjson_tokens(
        self,
        set_code: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        mtgjson_tokens = OrderedDict()
        print(f"Supporting {set_code}")
        mtgjson_tokens[set_code] = self.__all_printings.get_tokens_from_set_code(
            set_code
        )
        for child_set_code in self.__set_code_to_children_set_codes.get(set_code, []):
            print(f"Supporting {child_set_code} for {set_code}")
            mtgjson_tokens[child_set_code] = (
                self.__all_printings.get_tokens_from_set_code(child_set_code)
            )
        return mtgjson_tokens

    def get_associated_set_codes(self, set_code: str) -> Set[int]:
        return self.__set_code_to_group_ids.get(set_code, {})

    def get_iter(self) -> Dict[str, Set[int]]:
        return self.__set_code_to_group_ids

from typing import Dict, Set, OrderedDict, List, Any

from .all_printings import AllPrintings


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
        self.__set_code_to_group_ids["ONE"].add(1163)
        self.__set_code_to_group_ids["MOM"].add(1163)
        self.__set_code_to_group_ids["WOE"].add(1163)
        self.__set_code_to_group_ids["MKM"].add(1163)
        self.__set_code_to_group_ids["FIN"].add(1163)
        self.__set_code_to_group_ids["DMU"].add(1163)
        self.__set_code_to_group_ids["J25"].add(23792)

    def get_associated_mtgjson_tokens(
        self,
        set_code: str,
    ) -> Dict[str, List[Dict[str, Any]]]:
        mtgjson_tokens = OrderedDict()
        print(f"MTGJSON: Supporting {set_code}")
        mtgjson_tokens[set_code] = self.__all_printings.get_tokens_from_set_code(
            set_code
        )
        for child_set_code in self.__set_code_to_children_set_codes.get(set_code, []):
            print(f"MTGJSON: Supporting {child_set_code} for {set_code}")
            mtgjson_tokens[child_set_code] = (
                self.__all_printings.get_tokens_from_set_code(child_set_code)
            )
        return mtgjson_tokens

    def get_codes_to_group_ids_mapping(self) -> Dict[str, Set[int]]:
        return self.__set_code_to_group_ids

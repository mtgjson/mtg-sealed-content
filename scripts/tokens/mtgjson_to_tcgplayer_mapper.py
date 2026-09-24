import re
from collections import defaultdict
from collections.abc import Callable

import unidecode
from typing import Dict, List, Any, Optional, Tuple


class MtgjsonToTcgplayerMapper:
    bio_regex: re.Pattern
    decklist_regex: re.Pattern

    def __init__(self) -> None:
        self.bio_regex = re.compile(r"(\d+) (.*) Biography")
        self.decklist_regex = re.compile(r"(\d+) (.*) Decklist")
        self.wc_blank_regex = re.compile(r"(\d+) World Championship Blank Card")

    @staticmethod
    def strip_star(number: str | None) -> str | None:
        if number:
            return number.replace("*", "").replace("★", "")
        return ""

    @staticmethod
    def strip_quotes(mtgjson_token_name: str) -> str:
        return mtgjson_token_name.replace('"', "")

    def compare_face_name_and_number(
        self, tcgplayer_face_name, tcgplayer_face_id, mtgjson_name, mtgjson_number
    ):
        name_match = unidecode.unidecode(tcgplayer_face_name) == unidecode.unidecode(
            self.strip_quotes(mtgjson_name)
        )

        mtgjson_clean_num = self.strip_star(mtgjson_number)
        if not mtgjson_clean_num:
            return False

        number_match = self.compare_numbers_safely(mtgjson_clean_num, tcgplayer_face_id)

        return name_match and number_match

    @staticmethod
    def add_uuid_to_list(
        tcgplayer_token_face_details, tcgplayer_token_face_index, mtgjson_token
    ):
        if "uuids" not in tcgplayer_token_face_details[tcgplayer_token_face_index]:
            tcgplayer_token_face_details[tcgplayer_token_face_index]["uuids"] = []
        tcgplayer_token_face_details[tcgplayer_token_face_index]["uuids"].append(
            mtgjson_token["uuid"]
        )

    @staticmethod
    def compare_numbers_safely(mtgjson_num: str, tcgplayer_id: str) -> bool:
        if not mtgjson_num:
            return False

        if mtgjson_num == tcgplayer_id:
            return True

        if mtgjson_num.endswith("s") and mtgjson_num.rstrip("s") == tcgplayer_id:
            return True

        return False

    def match_art_card(self, mtgjson_token, tcgplayer_token_face):
        if mtgjson_token["layout"] != "art_series":
            return False

        if self.compare_face_name_and_number(
            f"{tcgplayer_token_face['faceName']} // {tcgplayer_token_face['faceName']}",
            tcgplayer_token_face["faceId"],
            mtgjson_token["name"],
            mtgjson_token["number"],
        ):
            return True

        if unidecode.unidecode(
            f"{tcgplayer_token_face['faceName']} //"
        ) in unidecode.unidecode(
            self.strip_quotes(mtgjson_token["name"])
        ) or unidecode.unidecode(
            f"// {tcgplayer_token_face['faceName']}"
        ) in unidecode.unidecode(
            self.strip_quotes(mtgjson_token["name"])
        ):
            return True

        return False

    def match_theme_card(self, mtgjson_token, tcgplayer_token_face):
        if mtgjson_token["layout"] != "token":
            return False
        return self.compare_face_name_and_number(
            tcgplayer_token_face["faceName"],
            tcgplayer_token_face["faceId"],
            mtgjson_token["name"],
            mtgjson_token["number"],
        )

    def match_bio_card(self, mtgjson_token, tcgplayer_token_face):
        if match := self.bio_regex.match(tcgplayer_token_face["faceName"]):
            result = unidecode.unidecode(str(match.group(2)) + " Bio")
            year = match.group(1)
            if (
                unidecode.unidecode(mtgjson_token["name"]) == result
                or unidecode.unidecode(mtgjson_token["name"]) == result + f" ({year})"
                or unidecode.unidecode(mtgjson_token["name"]) == result + f" {year}"
            ):
                return True

        return False

    def match_decklist_card(self, mtgjson_token, tcgplayer_token_face):
        if match := self.decklist_regex.match(tcgplayer_token_face["faceName"]):
            result = str(match.group(2)) + " Decklist"
            year = str(match.group(1))
            if (
                unidecode.unidecode(mtgjson_token["name"]) == result
                or unidecode.unidecode(mtgjson_token["name"]) == result + f" ({year})"
                or unidecode.unidecode(mtgjson_token["name"]) == result + f" {year}"
            ):
                return True
        return False

    def handle_art_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if not self.match_art_card(mtgjson_token, tcgplayer_token_face):
            return False
        print(f"> Found Art Card for {tcgplayer_token_face}")
        self.add_uuid_to_list(
            tcgplayer_token_face_details,
            tcgplayer_token_face_index,
            mtgjson_token,
        )
        return True

    def handle_theme_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if not self.match_theme_card(mtgjson_token, tcgplayer_token_face):
            return False
        print(f"> Found Theme Card for {tcgplayer_token_face}")

        self.add_uuid_to_list(
            tcgplayer_token_face_details,
            tcgplayer_token_face_index,
            mtgjson_token,
        )
        return True

    def handle_tokens(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):

        mtgjson_token_number = mtgjson_token["number"].split("-")[-1]
        if mtgjson_token_number[0].isalpha() and set_code in {"MED"}:
            mtgjson_token_number = str(mtgjson_token_number[1:])

        if self.compare_face_name_and_number(
            tcgplayer_token_face["faceName"],
            tcgplayer_token_face["faceId"],
            (
                mtgjson_token.get("faceName", mtgjson_token.get("name"))
                if set_code in {"UST"}
                else mtgjson_token["name"]
            ),
            mtgjson_token_number,
        ):
            print(f"> Found Token for {tcgplayer_token_face}")

            self.add_uuid_to_list(
                tcgplayer_token_face_details,
                tcgplayer_token_face_index,
                mtgjson_token,
            )
            return True

        if (
            mtgjson_token["layout"] == "double_faced_token"
        ) and self.compare_face_name_and_number(
            tcgplayer_token_face["faceName"],
            tcgplayer_token_face["faceId"],
            mtgjson_token["name"],
            mtgjson_token["number"],
        ):
            print(f"> Found DF Token for {tcgplayer_token_face}")
            self.add_uuid_to_list(
                tcgplayer_token_face_details,
                tcgplayer_token_face_index,
                mtgjson_token,
            )
            return True

        # OTJ Bounty Cards are weird
        if mtgjson_token["layout"] == "double_faced_token" and mtgjson_token[
            "name"
        ].startswith("Bounty:"):
            if tcgplayer_token_face["faceId"] == mtgjson_token["number"]:
                print(f"> Found Bounty Token for {tcgplayer_token_face}")
                self.add_uuid_to_list(
                    tcgplayer_token_face_details,
                    tcgplayer_token_face_index,
                    mtgjson_token,
                )
                return True

        return False

    def handle_punch_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if (tcgplayer_token_face["faceName"] == "Punchcard") and (
            mtgjson_token["name"] == "Punchcard // Punchcard"
        ):
            print(f"> Found Punch Token for {tcgplayer_token_face}")
            self.add_uuid_to_list(
                tcgplayer_token_face_details,
                tcgplayer_token_face_index,
                mtgjson_token,
            )
            return True

        return False

    def handle_helper_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if (
            tcgplayer_token_face["faceName"] == "Helper Card"
            and tcgplayer_token_face["faceId"] == mtgjson_token["number"]
            and mtgjson_token["type"] == "Card"
            and "Substitute" in mtgjson_token["name"]
        ):
            print(f"> Found Helper Token for {tcgplayer_token_face}")
            self.add_uuid_to_list(
                tcgplayer_token_face_details,
                tcgplayer_token_face_index,
                mtgjson_token,
            )
            return True

        return False

    def handle_decklist_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if not self.match_decklist_card(mtgjson_token, tcgplayer_token_face):
            return False
        print(f"> Found Decklist for {tcgplayer_token_face}")
        self.add_uuid_to_list(
            tcgplayer_token_face_details,
            tcgplayer_token_face_index,
            mtgjson_token,
        )
        return True

    def handle_minigame_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        # print(f">>>> {tcgplayer_token_face['faceName']} vs {mtgjson_token.get('faceName', '')}")
        # print(f">>>> {tcgplayer_token_face['faceId']} vs {mtgjson_token.get('number', '')}")

        if tcgplayer_token_face["faceName"].strip() == "Find The Assassin":
            if mtgjson_token.get("faceName", "").lower() == "find the assassin":
                pass

        if self.compare_face_name_and_number(
            tcgplayer_token_face["faceName"].lower(),
            tcgplayer_token_face["faceId"],
            mtgjson_token.get("faceName", "").lower(),
            mtgjson_token["number"],
        ):
            print(f"> Found Minigame for {tcgplayer_token_face}")

            self.add_uuid_to_list(
                tcgplayer_token_face_details,
                tcgplayer_token_face_index,
                mtgjson_token,
            )
            return True

        return False

    def handle_bio_cards(
        self,
        set_code,
        mtgjson_token,
        tcgplayer_token_face_details,
        tcgplayer_token_face_index,
        tcgplayer_token_face,
    ):
        if not self.match_bio_card(mtgjson_token, tcgplayer_token_face):
            return False

        print(f"> Found Bio for {tcgplayer_token_face}")
        self.add_uuid_to_list(
            tcgplayer_token_face_details,
            tcgplayer_token_face_index,
            mtgjson_token,
        )
        return True

    # TCGplayer sells these treatments as their own products, and MTGJSON gives
    # them their own collector number with a star suffix. Anything else (plain
    # foil, for instance) is a SKU of the same product, not a separate one.
    FOIL_TREATMENT_KEYWORDS = (
        "surge foil",
        "rainbow foil",
        "textured foil",
        "galaxy foil",
        "etched foil",
        "foil etched",
        "step-and-compleat foil",
        "oil slick",
        "halo foil",
        "confetti foil",
    )

    @staticmethod
    def build_uuid_index(
        mtgjson_tokens: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Tuple[str, Dict[str, Any]]]:
        index = {}
        for set_code, mtgjson_token_data in mtgjson_tokens.items():
            for mtgjson_token in mtgjson_token_data:
                index[mtgjson_token["uuid"]] = (set_code, mtgjson_token)
        return index

    @classmethod
    def product_prefers_foil_printing(
        cls, tcgplayer_token: Dict[str, Any], tcgplayer_token_face: Dict[str, Any]
    ) -> bool:
        name = str(tcgplayer_token.get("name", "")).lower()
        if any(keyword in name for keyword in cls.FOIL_TREATMENT_KEYWORDS):
            return True
        return any(
            "foil" in str(attribute).lower()
            for attribute in tcgplayer_token_face.get("faceAttribute", [])
        )

    @staticmethod
    def product_prefers_stamped_printing(
        tcgplayer_token: Dict[str, Any], tcgplayer_token_face: Dict[str, Any]
    ) -> bool:
        """
        Gold-stamped signature art cards are their own TCGplayer product, and
        MTGJSON gives them an 's' suffix on the collector number.
        """
        if "gold-stamped" in str(tcgplayer_token.get("name", "")).lower():
            return True
        return any(
            "stamped" in str(attribute).lower()
            for attribute in tcgplayer_token_face.get("faceAttribute", [])
        )

    @staticmethod
    def printing_axes(prefers_foil: bool, prefers_stamped: bool):
        """
        The ways an otherwise identical pair of tokens can differ when TCGplayer
        sells them as two products. Each one answers "is this the printing the
        product is for?".
        """

        # "Etched Foil" products are printed with the 'etched' finish rather
        # than 'foil', so a foil product must accept either one.
        wanted_finishes = {"foil", "etched"} if prefers_foil else {"nonfoil"}

        def has_wanted_finish(mtgjson_token: Dict[str, Any]) -> bool:
            finishes = mtgjson_token.get("finishes") or []
            return bool(wanted_finishes.intersection(finishes))

        def has_wanted_stamp(mtgjson_token: Dict[str, Any]) -> bool:
            promo_types = mtgjson_token.get("promoTypes") or []
            return ("stamped" in promo_types) == prefers_stamped

        return (has_wanted_finish, has_wanted_stamp)

    @classmethod
    def number_match_rank(cls, mtgjson_number: str, tcgplayer_face_id: str):
        """
        How much mangling it took to make an MTGJSON collector number look like
        the number TCGplayer prints on a face. Lower is a closer match, and None
        means the two never line up. The transformations mirror the ones applied
        while matching; ranking them is what keeps '4' from losing to '4*' and
        'TAFR-1' from being interchangeable with 'TGRN-1'.
        """
        if not mtgjson_number or not tcgplayer_face_id:
            return None

        best = None
        for prefix_cost, without_prefix in (
            (0, mtgjson_number),
            (4, mtgjson_number.split("-")[-1]),
        ):
            for star_cost, without_star in (
                (0, without_prefix),
                (2, cls.strip_star(without_prefix)),
            ):
                forms = [(0, without_star)]
                if without_star.endswith("s"):
                    forms.append((1, without_star[:-1]))
                for suffix_cost, form in forms:
                    if form and form == tcgplayer_face_id:
                        cost = prefix_cost + star_cost + suffix_cost
                        best = cost if best is None else min(best, cost)
        return best

    @classmethod
    def resolve_candidate_uuids(
        cls,
        candidate_uuids: List[str],
        uuid_index: Dict[str, Tuple[str, Dict[str, Any]]],
        tcgplayer_face_id: str,
        product_group_id: int = None,
        set_code_to_group_id: Dict[str, int] = None,
        prefers_foil: bool = False,
        prefers_stamped: bool = False,
    ) -> List[str]:
        """
        A TCGplayer face names one printed token, so it belongs to exactly one
        MTGJSON UUID. Name-and-number matching routinely finds several, and
        publishing all of them is what puts a Commander-deck Zombie on a
        main-set product. Narrow the field instead, in order of how much we
        trust each signal.
        """
        candidates = [
            (uuid, *uuid_index[uuid]) for uuid in candidate_uuids if uuid in uuid_index
        ]
        if len(candidates) <= 1:
            return [uuid for uuid, _, _ in candidates] or list(candidate_uuids)

        # The product was pulled from one TCGplayer group, and each MTGJSON set
        # belongs to one group. Anything from another set is not this product.
        if product_group_id is not None and set_code_to_group_id:
            in_group = [
                candidate
                for candidate in candidates
                if set_code_to_group_id.get(candidate[1]) == product_group_id
            ]
            if in_group:
                candidates = in_group

        # A star or 's' suffix on the collector number marks a printing that
        # TCGplayer sells as its own product: a surge foil, or a gold-stamped
        # signature art card. Only the treatment named on the product tells
        # those apart from the plain printing, never the number.
        if cls.__is_printing_variant_group(candidates):
            for is_wanted_printing in cls.printing_axes(prefers_foil, prefers_stamped):
                if len(candidates) < 2:
                    break
                matching = [
                    candidate
                    for candidate in candidates
                    if is_wanted_printing(candidate[2])
                ]
                if matching and len(matching) < len(candidates):
                    candidates = matching

        if len(candidates) > 1:
            ranked = [
                (cls.number_match_rank(candidate[2].get("number"), tcgplayer_face_id), candidate)
                for candidate in candidates
            ]
            ranked = [(rank, candidate) for rank, candidate in ranked if rank is not None]
            if ranked:
                closest = min(rank for rank, _ in ranked)
                candidates = [
                    candidate for rank, candidate in ranked if rank == closest
                ]

        # Both halves of a two-sided token carry the same combined name and
        # number, so a face that matched on the name matched both of them. The
        # front is the one that stands for the card; the back still gets its own
        # entry further down the pipeline.
        if len(candidates) > 1 and cls.__differ_only_by_side(candidates):
            fronts = [
                candidate
                for candidate in candidates
                if (candidate[2].get("side") or "a") == "a"
            ]
            if fronts:
                candidates = fronts

        return [uuid for uuid, _, _ in candidates]

    @staticmethod
    def __is_printing_variant_group(candidates) -> bool:
        return (
            len({candidate[1] for candidate in candidates}) == 1
            and len({candidate[2].get("name") for candidate in candidates}) == 1
        )

    @staticmethod
    def __differ_only_by_side(candidates) -> bool:
        return (
            len(
                {
                    (candidate[1], candidate[2].get("name"), candidate[2].get("number"))
                    for candidate in candidates
                }
            )
            == 1
        )

    def add_mtgjson_uuids_to_tcgplayer_token_face_details(
        self,
        set_code,
        mtgjson_tokens: Dict[str, List[Dict[str, Any]]],
        tcgplayer_token_face_details: List[Dict[str, Any]],
        tcgplayer_token: Optional[Dict[str, Any]] = None,
        set_code_to_group_id: Optional[Dict[str, int]] = None,
        uuid_index: Optional[Dict[str, Tuple[str, Dict[str, Any]]]] = None,
    ) -> List[Dict[str, Any]]:
        print(f"Looking for {tcgplayer_token_face_details}")

        tcgplayer_token = tcgplayer_token or {}
        if uuid_index is None:
            uuid_index = self.build_uuid_index(mtgjson_tokens)
        unresolved: List[Dict[str, Any]] = []

        # A treatment names the whole physical card even when TCGplayer prints
        # it after one face's name, so both faces want the same printing.
        prefers_foil = any(
            self.product_prefers_foil_printing(tcgplayer_token, face)
            for face in tcgplayer_token_face_details
        )
        prefers_stamped = any(
            self.product_prefers_stamped_printing(tcgplayer_token, face)
            for face in tcgplayer_token_face_details
        )

        function_mapping: Dict[str, Callable[[Any, Any, Any, Any, Any], bool]] = {
            "Art": self.handle_art_cards,
            "Theme": self.handle_theme_cards,
            "Token": self.handle_tokens,
            "Punch": self.handle_punch_cards,
            "Helper": self.handle_helper_cards,
            "Bio": self.handle_bio_cards,
            "Decklist": self.handle_decklist_cards,
            "Minigame": self.handle_minigame_cards,
        }

        for tcgplayer_token_face_index, tcgplayer_token_face in enumerate(
            tcgplayer_token_face_details
        ):
            found = False
            for mtgjson_token_data in mtgjson_tokens.values():
                for mtgjson_token in mtgjson_token_data:
                    if tcgplayer_token_face["tokenType"] in function_mapping:
                        new_found = function_mapping[tcgplayer_token_face["tokenType"]](
                            set_code,
                            mtgjson_token,
                            tcgplayer_token_face_details,
                            tcgplayer_token_face_index,
                            tcgplayer_token_face,
                        )
                        found = found or new_found

            if not found:
                print(f">> UNABLE to find UUID for {tcgplayer_token_face}")
                continue

            candidates = tcgplayer_token_face.get("uuids", [])
            if len(candidates) < 2:
                continue

            resolved = self.resolve_candidate_uuids(
                candidates,
                uuid_index,
                tcgplayer_token_face.get("faceId"),
                product_group_id=tcgplayer_token.get("groupId"),
                set_code_to_group_id=set_code_to_group_id,
                prefers_foil=prefers_foil,
                prefers_stamped=prefers_stamped,
            )

            if len(resolved) == 1:
                print(
                    f"> Narrowed {len(candidates)} candidates to {resolved[0]} "
                    f"for {tcgplayer_token_face['faceName']}"
                )
                tcgplayer_token_face["uuids"] = resolved
                continue

            # Publishing every candidate is how a product ends up claiming a
            # token it is not. Drop the face and surface it for review instead.
            print(
                f">> AMBIGUOUS face {tcgplayer_token_face['faceName']} on product "
                f"{tcgplayer_token.get('productId')}: {resolved}"
            )
            unresolved.append(
                {
                    "productId": tcgplayer_token.get("productId"),
                    "productName": tcgplayer_token.get("name"),
                    "parentSetCode": set_code,
                    "faceName": tcgplayer_token_face.get("faceName"),
                    "faceId": tcgplayer_token_face.get("faceId"),
                    "candidates": [
                        {
                            "uuid": uuid,
                            "setCode": uuid_index[uuid][0],
                            "number": uuid_index[uuid][1].get("number"),
                        }
                        for uuid in resolved
                        if uuid in uuid_index
                    ],
                }
            )
            del tcgplayer_token_face["uuids"]

        return unresolved

    @staticmethod
    def front_to_back_mapping(mtgjson_tokens) -> Dict[str, str]:
        """
        A two-sided token is one product, so both of its UUIDs should point at
        that product. Faces are matched to the front, and this carries the
        result over to the back. Sides are paired by printing rather than by
        list position, because a set can hold several printings of the same
        card.
        """
        sides_by_printing = defaultdict(dict)

        for set_code, mtgjson_token_data in mtgjson_tokens.items():
            for mtgjson_token in mtgjson_token_data:
                side = mtgjson_token.get("side")
                if side not in ("a", "b"):
                    continue
                printing = (
                    set_code,
                    mtgjson_token["name"],
                    mtgjson_token["number"],
                )
                sides_by_printing[printing][side] = mtgjson_token["uuid"]

        front_to_back_mapping = {}
        for printing, sides in sides_by_printing.items():
            if "a" in sides and "b" in sides:
                front_to_back_mapping[sides["a"]] = sides["b"]
            else:
                print(f"Unable to pair both sides for {printing}")

        return front_to_back_mapping

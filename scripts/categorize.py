import re
import json
import yaml
import logging
import requests
from enum import Enum
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from functools import cached_property
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Self, List

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class Category(str, Enum):
    BOOSTER_PACK = "BOOSTER_PACK"
    BOOSTER_BOX = "BOOSTER_BOX"
    BOOSTER_CASE = "BOOSTER_CASE"
    BOX = "BOX"
    BOX_SET = "BOX_SET"
    BUNDLE = "BUNDLE"
    BUNDLE_CASE = "BUNDLE_CASE"
    CASE = "CASE"
    DECK = "DECK"
    DECK_BOX = "DECK_BOX"
    KIT = "KIT"
    LIMITED = "LIMITED"
    LIMITED_CASE = "LIMITED_CASE"
    MULTI_DECK = "MULTI_DECK"
    SUBSET = "SUBSET"
    UNKNOWN = "UNKNOWN"

class Subtype(str, Enum):
    ADVANCED = "ADVANCED"
    ARCHENEMY = "ARCHENEMY"
    BATTLE = "BATTLE"
    BRAWL = "BRAWL"
    CHALLENGE = "CHALLENGE"
    CHALLENGER = "CHALLENGER"
    CHAMPIONSHIP = "CHAMPIONSHIP"
    CLASH = "CLASH"
    COLLECTOR = "COLLECTOR"
    COLLECTORS_EDITION = "COLLECTORS_EDITION"
    COMMANDER = "COMMANDER"
    COMMANDER_COLLECTION = "COMMANDER_COLLECTION"
    CONVENTION = "CONVENTION"
    DECK_BUILDERS_TOOLKIT = "DECK_BUILDERS_TOOLKIT"
    DEFAULT = "DEFAULT"
    DRAFT = "DRAFT"
    DRAFT_SET = "DRAFT_SET"
    DUEL = "DUEL"
    EVENT = "EVENT"
    FAT_PACK = "FAT_PACK"
    FROM_THE_VAULT = "FROM_THE_VAULT"
    GAME_NIGHT = "GAME_NIGHT"
    GIFT_BUNDLE = "GIFT_BUNDLE"
    GUILD_KIT = "GUILD_KIT"
    INTRO = "INTRO"
    JUMPSTART = "JUMPSTART"
    LAND_STATION = "LAND_STATION"
    MINIMAL = "MINIMAL"
    OTHER = "OTHER"
    PLANECHASE = "PLANECHASE"
    PLANESWALKER = "PLANESWALKER"
    PLAY = "PLAY"
    PREMIUM = "PREMIUM"
    PRERELEASE = "PRERELEASE"
    PROMOTIONAL = "PROMOTIONAL"
    REDEMPTION = "REDEMPTION"
    SEALED_SET = "SEALED_SET"
    SECRET_LAIR = "SECRET_LAIR"
    SECRET_LAIR_BUNDLE = "SECRET_LAIR_BUNDLE"
    SECRET_LAIR_DROP = "SECRET_LAIR_DROP"
    SET = "SET"
    SIX = "SIX"
    SPELLBOOK = "SPELLBOOK"
    STARTER = "STARTER"
    STARTER_DECK = "STARTER" # Alias 
    THEME = "THEME"
    TOPPER = "TOPPER"
    TOURNAMENT = "TOURNAMENT"
    TWO_PLAYER_STARTER = "TWO_PLAYER_STARTER"
    WELCOME = "WELCOME"
    BEGINNER_BOX = "BEGINNER_BOX"
    UNKNOWN = "UNKNOWN"

@dataclass
class PurchaseUrl:
    location: str = ""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        return cls(location=data.get("location", ""))

    def to_dict(self) -> Dict[str, str]:
        return {"location": self.location}

@dataclass
class Product:
    language: str
    category: Category
    subtype: Subtype
    identifiers: Dict[str, str] = field(default_factory=dict)
    release_date: Optional[str] = None
    purchase_url: PurchaseUrl = field(default_factory=PurchaseUrl)

    def __post_init__(self):
        if isinstance(self.category, str):
            self.category = Category(self.category)
        if isinstance(self.subtype, str):
            self.subtype = Subtype(self.subtype)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Self:
        return cls(
            language=data.get('language', 'en'),
            category=Category(data.get('category', 'UNKNOWN')),
            subtype=Subtype(data.get('subtype', 'DEFAULT')),
            identifiers=data.get('identifiers', {}).copy(),
            release_date=data.get('release_date'),
            purchase_url=PurchaseUrl.from_dict(data.get('purchase_url', {}))
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            'language': self.language,
            'category': self.category.value,
            'subtype': self.subtype.value,
            'identifiers': self.identifiers,
            'release_date': self.release_date,
            'purchase_url': self.purchase_url.to_dict()
        }

    def merge_with(self, other: 'Product') -> None:
        if self.category == Category.UNKNOWN and other.category != Category.UNKNOWN:
            self.category = other.category
        if self.subtype in (Subtype.DEFAULT, Subtype.UNKNOWN) and other.subtype != Subtype.DEFAULT:
            self.subtype = other.subtype

        if not self.release_date and other.release_date:
            self.release_date = other.release_date

        if not self.language and other.language:
            self.language = other.language

        self.identifiers.update(other.identifiers)

@dataclass
class ReleaseSet:
    code: str
    products: Dict[str, Product] = field(default_factory=dict)

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalization for product name matching"""
        normalized = name.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        words = normalized.split()
        words.sort()
        normalized = ' '.join(words)
        
        return normalized

    @staticmethod
    def _clean_product_name(name: str) -> str:
        """Remove unwanted prefixes from product names"""
        prefixes_to_remove = [
            r'^Commander:\s*Magic:\s*The\s*Gathering\s*\|\s*',
            r'^Magic:\s*The\s*Gathering\s*\|\s*',
        ]
        
        cleaned = name
        for prefix_pattern in prefixes_to_remove:
            cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()

    @classmethod
    def from_yaml_file(cls, file_path: Path) -> Self:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        products = {
            cls._clean_product_name(name): Product.from_dict(prod_data)
            for name, prod_data in data.get("products", {}).items()
        }
        return cls(code=data.get("set_code", ""), products=products)

    def to_yaml_file(self, output_dir: Path) -> Path:
        if not self.code or self.code.strip() == '':
            self.code = "UNKNOWN"

        output_path = output_dir / f"{self.code.upper()}.yaml"
        data = {
            "set_code": self.code,
            "products": {
                name: product.to_dict()
                for name, product in sorted(self.products.items())
            },
        }
        output_path.write_text(
            yaml.dump(data, default_flow_style=False, sort_keys=False, width=120),
            encoding="utf-8",
        )
        logger.info(f"Written {len(self.products)} products to {output_path}")
        return output_path

    def add_or_merge_product(self, name: str, product: Product) -> None:
        clean_name = self._clean_product_name(name)
        
        if clean_name in self.products:
            self.products[clean_name].merge_with(product)
            return

        normalized = self._normalize_name(clean_name)
        for existing_name in self.products:
            if self._normalize_name(existing_name) == normalized:
                better_name = self._choose_better_name(existing_name, clean_name)
                
                if better_name != existing_name:
                    self.products[better_name] = self.products.pop(existing_name)
                    self.products[better_name].merge_with(product)
                    logger.debug(f"Merged product '{clean_name}' into '{better_name}' (replaced '{existing_name}')")
                else:
                    self.products[existing_name].merge_with(product)
                    logger.debug(f"Merged product '{clean_name}' into existing '{existing_name}'")
                return

        self.products[clean_name] = product

    @staticmethod
    def _choose_better_name(name1: str, name2: str) -> str:
        """Choose the better formatted name between two variants"""
        score1 = ReleaseSet._name_quality_score(name1)
        score2 = ReleaseSet._name_quality_score(name2)
        return name1 if score1 >= score2 else name2
    
    @staticmethod
    def _name_quality_score(name: str) -> int:
        """Score a product name's quality (higher is better)"""
        score = 0
        
        if ':' in name:
            score += 10
        
        if '""' in name:
            score -= 20
        
        if re.search(r':\s*"[^"]+"\s+', name):
            score += 15

        if re.search(r'\s+(commander|deck|booster|bundle|pack)\s+\w+$', name.lower()):
            if not name.lower().endswith(('commander deck', 'booster pack', 'booster box')):
                score -= 5
        
        score -= len(name) // 10
        
        return score
    
@dataclass
class ScryfallCache:
    """Manages local caching of Scryfall sets data"""
    
    cache_file: Path = field(default_factory=lambda: Path("data/scryfall_sets_cache.json"))
    cache_duration_days: int = 1

    def is_valid(self) -> bool:
        if not self.cache_file.exists():
            return False
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                cache_date = datetime.fromisoformat(data.get('cached_at', '2000-01-01'))
                age = datetime.now() - cache_date
                return age < timedelta(days=self.cache_duration_days)
        except Exception as e:
            logger.warning(f"Cache validation failed: {e}")
            return False

    def load(self) -> List[Dict]:
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.info(f"Loaded {len(data['sets'])} sets from cache")
                return data['sets']
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
            return []

    def save(self, sets_data: List[Dict]) -> None:
        try:
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {
                'cached_at': datetime.now().isoformat(),
                'sets': sets_data
            }
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2)
            logger.info(f"Cached {len(sets_data)} sets to {self.cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")

@dataclass
class SetResolver:
    """Extracts, groups, and resolves MTG set names to official set codes"""
    cache: ScryfallCache = field(default_factory=ScryfallCache)
    _sets_data: Optional[List[Dict]] = field(default=None, init=False, repr=False)
    _code_cache: Dict[str, str] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self):
        self._load_sets_data()

    @cached_property
    def _removal_pattern(self) -> re.Pattern:
        product_phrases = {
            *[cat.value.lower().replace("_", r"\s+") for cat in Category],
            *[sub.value.lower().replace("_", r"\s+") for sub in Subtype],
        }
        pattern = r"\s+(" + "|".join(sorted(product_phrases, key=len, reverse=True)) + r").*$"
        return re.compile(pattern, re.IGNORECASE)

    def extract_set_name(self, product_name: str) -> Optional[str]:
        """Extract clean set name from product name"""
        name_lower = product_name.lower()

        if "could not load" in name_lower:
            return None

        if "secret lair" in name_lower:
            return "Secret Lair"

        clean = re.sub(
            r"^(commander|magic:\s*the\s+gathering|the\s+gathering)\s*[-|:]?\s*",
            "",
            name_lower,
            flags=re.IGNORECASE,
        )

        clean = self._removal_pattern.sub("", clean)
        clean = re.sub(r'\s+[\"\"\"\']+.*$', "", clean)
        clean = re.sub(r"[\s\-:|]+$", "", clean).strip()

        if not clean or len(clean) <= 3:
            return None

        return clean.title()

    @staticmethod
    def normalize_for_grouping(name: str) -> str:
        """Normalize set name for fuzzy grouping"""
        normalized = name.lower().replace("'s", "s").translate(str.maketrans("-_|:", "    "))
        normalized = re.sub(r"[^a-z0-9\s]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def group_set_names(self, set_names: set[str]) -> Dict[str, str]:
        """Group similar set names to canonical names"""
        normalized_map = {
            name: self.normalize_for_grouping(name) for name in set_names
        }
        subseq_to_names = self._build_subsequence_index(set_names, normalized_map)
        canonical_map = self._find_canonical_names(set_names, normalized_map, subseq_to_names)
        self._log_groupings(canonical_map)
        return canonical_map

    @staticmethod
    def _build_subsequence_index(
        set_names: set[str], normalized_map: Dict[str, str]
    ) -> Dict[str, set[str]]:
        subseq_to_names = defaultdict(set)
        for raw_name in set_names:
            words = normalized_map[raw_name].split()
            for length in range(1, len(words) + 1):
                for start in range(len(words) - length + 1):
                    subseq = " ".join(words[start : start + length])
                    subseq_to_names[subseq].add(raw_name)
        return subseq_to_names

    @staticmethod
    def _find_canonical_names(
        set_names: set[str],
        normalized_map: Dict[str, str],
        subseq_to_names: Dict[str, set[str]],
    ) -> Dict[str, str]:
        canonical_map = {}
        for raw_name in set_names:
            words = normalized_map[raw_name].split()
            best_subseq = max(
                (
                    " ".join(words[start : start + length])
                    for length in range(1, len(words) + 1)
                    for start in range(len(words) - length + 1)
                ),
                key=lambda s: (len(subseq_to_names[s]), len(s.split())),
                default=None,
            )
            if best_subseq:
                matching_names = [
                    n for n in subseq_to_names[best_subseq] if best_subseq in normalized_map[n]
                ]
                canonical = min(matching_names, key=lambda x: len(normalized_map[x]))
                canonical_map[raw_name] = canonical
            else:
                canonical_map[raw_name] = raw_name
        return canonical_map

    @staticmethod
    def _log_groupings(canonical_map: Dict[str, str]) -> None:
        groups = defaultdict(list)
        for name, canonical in canonical_map.items():
            groups[canonical].append(name)

        logger.info("Fuzzy grouping results:")
        for canonical in sorted(groups.keys()):
            group = groups[canonical]
            logger.info(f"  {canonical} (n={len(group)})")
            for name in sorted(group):
                if name != canonical:
                    logger.info(f"    -> {name}")

    def find_set_code(self, set_name: str) -> str:
        """Find official Scryfall set code for a set name"""
        if not set_name or not set_name.strip():
            return "unknown"

        cache_key = set_name.lower().strip()

        if cache_key in self._code_cache:
            logger.debug(f"Memory cache hit: '{set_name}' -> '{self._code_cache[cache_key]}'")
            return self._code_cache[cache_key]

        if not self._sets_data:
            logger.error("No sets data available")
            return "no_code"

        best_match = self._fuzzy_match_set(set_name)

        if best_match:
            code = best_match['code']
            self._code_cache[cache_key] = code
            logger.info(f"Matched: '{set_name}' -> '{code}' ({best_match['name']})")
            return code

        logger.warning(f"No match found for: '{set_name}'")
        return "no_code"

    def _load_sets_data(self) -> None:
        if self.cache.is_valid():
            logger.info("Loading sets from cache...")
            self._sets_data = self.cache.load()
        else:
            logger.info("Downloading sets from Scryfall API...")
            self._sets_data = self._download_from_scryfall()
            self.cache.save(self._sets_data)

    def _download_from_scryfall(self) -> List[Dict]:
        try:
            response = requests.get("https://api.scryfall.com/sets", timeout=10)
            response.raise_for_status()
            sets_data = response.json().get('data', [])

            filtered_sets = [
               s for s in sets_data
               if s.get('set_type') not in {
                   'token', 'memorabilia', 'alchemy', 'masterpiece'
               }
            ]
            logger.info(f"Downloaded {len(filtered_sets)} sets from Scryfall")
            return filtered_sets
        except Exception as e:
            logger.error(f"Failed to download sets from Scryfall: {e}")
            return []

    def _fuzzy_match_set(self, query: str) -> Optional[Dict]:
        from thefuzz import fuzz

        query_lower = query.lower().strip()
        query_normalized = self._normalize_scryfall_name(query_lower)

        PREFERRED_SET_TYPES = ['expansion', 'core', 'commander', 'draft_innovation', 'masters']

        candidates = []

        for set_data in self._sets_data:
            set_name = set_data.get('name', '')
            set_code = set_data.get('code', '')
            set_type = set_data.get('set_type', '')

            if not set_name:
                continue

            if query_lower == set_code.lower():
                logger.debug(f"Exact code match: '{query}' == '{set_code}'")
                return set_data

            if query_lower == set_name.lower():
                logger.debug(f"Exact name match: '{query}' == '{set_name}'")
                return set_data

            set_normalized = self._normalize_scryfall_name(set_name.lower())

            token_score = fuzz.token_sort_ratio(query_normalized, set_normalized)
            partial_score = fuzz.partial_ratio(query_normalized, set_normalized)
            ratio_score = fuzz.ratio(query_normalized, set_normalized)

            combined_score = (token_score * 0.5) + (partial_score * 0.3) + (ratio_score * 0.2)

            type_bonus = 0
            if set_type in PREFERRED_SET_TYPES:
                type_bonus = 10

            final_score = combined_score + type_bonus

            candidates.append({
                'data': set_data,
                'name': set_name,
                'code': set_code,
                'type': set_type,
                'score': combined_score,
                'final_score': final_score
            })

        candidates.sort(key=lambda x: x['final_score'], reverse=True)

        if not candidates or candidates[0]['score'] < 70:
            logger.warning(f"No match for '{query}' (normalized: '{query_normalized}'). Top candidates:")
            for c in candidates[:5]:
                logger.warning(f"  {c['score']:.1f}% ({c['type']}) - {c['code']}: {c['name']}")
            return None

        best = candidates[0]
        logger.debug(f"Fuzzy match: '{query}' -> '{best['name']}' [{best['type']}] (score: {best['score']:.1f})")
        return best['data']

    @staticmethod
    def _normalize_scryfall_name(name: str) -> str:
        """Normalize name for Scryfall matching (different from grouping normalization)"""
        name = re.sub(r'^(magic:?\s*the\s*gathering\s*[-:]?\s*|mtg\s*[-:]?\s*)', '', name, flags=re.IGNORECASE)
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', ' ', name)
        return name.strip()

@dataclass
class ProductProcessor:
    set_resolver: SetResolver = field(default_factory=SetResolver)
        
    @cached_property
    def category_patterns(self) -> list[Tuple[re.Pattern, Category]]:
        patterns = [
            (r"master\s*case", Category.BOOSTER_CASE),
            (r"booster.*display.*case", Category.BOOSTER_CASE),
            (r"bundle\s+case", Category.BUNDLE_CASE),
            (r"prerelease.*case", Category.LIMITED_CASE),
            (r"collector.*booster.*box", Category.BOOSTER_BOX),
            (r"play.*booster.*box", Category.BOOSTER_BOX),
            (r"draft.*booster.*box", Category.BOOSTER_BOX),
            (r"booster.*display", Category.BOOSTER_BOX),
            (r"booster\s+box", Category.BOOSTER_BOX),
            (r"collector\s+booster(?!\s*(box|display|case))", Category.BOOSTER_PACK),
            (r"play\s+booster(?!\s*(box|display|case))", Category.BOOSTER_PACK),
            (r"draft\s+booster(?!\s*(box|display|case))", Category.BOOSTER_PACK),
            (r"booster\s+pack", Category.BOOSTER_PACK),
            (r"omega\s+pack", Category.BOOSTER_PACK),
            (r"deck\s+set", Category.MULTI_DECK),
            (r"commander.*set.*\d", Category.MULTI_DECK),
            (r"set\s+of\s+\d+", Category.MULTI_DECK),
            (r"commander\s+deck(?!\s*(set|display|case))", Category.DECK),
            (r"theme\s+deck(?!\s*(display|box))", Category.DECK),
            (r"planeswalker\s+deck", Category.DECK),
            (r"challenger\s+deck", Category.DECK),
            (r"60.*card.*deck", Category.DECK),
            (r"fat\s+pack\s+bundle", Category.BUNDLE),
            (r"fat\s+pack(?!\s*case)", Category.BUNDLE),
            (r"gift\s+bundle", Category.BUNDLE),
            (r"chocobo\s+bundle", Category.BUNDLE),
            (r"pizza\s+bundle", Category.BUNDLE),
            (r"bundle(?!\s*case)", Category.BUNDLE),
            (r"scene.*box.*set", Category.BOX_SET),
            (r"scene\s+box(?!\s*set)", Category.BOX),
            (r"draft\s+night(?!\s*case)", Category.KIT),
            (r"countdown\s+kit", Category.KIT),
            (r"turtle.*team.*up", Category.KIT),
            (r"prerelease\s+pack(?!\s*case)", Category.LIMITED),
            (r"secret\s+lair", Category.SUBSET),
        ]
        return [(re.compile(p, re.IGNORECASE), cat) for p, cat in patterns]

    @cached_property
    def subtype_patterns(self) -> list[Tuple[re.Pattern, Subtype]]:
        patterns = [
            (r"collector", Subtype.COLLECTOR),
            (r"play\s+booster", Subtype.PLAY),
            (r"draft", Subtype.DRAFT),
            (r"commander", Subtype.COMMANDER),
            (r"theme\s+deck", Subtype.THEME),
            (r"planeswalker", Subtype.PLANESWALKER),
            (r"challenger", Subtype.CHALLENGER),
            (r"starter", Subtype.STARTER),
            (r"fat\s+pack", Subtype.FAT_PACK),
            (r"gift\s+bundle", Subtype.GIFT_BUNDLE),
            (r"prerelease", Subtype.PRERELEASE),
            (r"secret\s+lair\s+bundle", Subtype.SECRET_LAIR_BUNDLE),
            (r"secret\s+lair", Subtype.SECRET_LAIR),
            (r"premium", Subtype.PREMIUM),
        ]
        return [(re.compile(p, re.IGNORECASE), sub) for p, sub in patterns]

    def categorize(self, product_name: str) -> Tuple[Category, Subtype]:
        category = next(
            (cat for pattern, cat in self.category_patterns if pattern.search(product_name)),
            Category.UNKNOWN,
        )
        subtype = next(
            (sub for pattern, sub in self.subtype_patterns if pattern.search(product_name)),
            Subtype.DEFAULT,
        )
        return category, subtype
    
    def process(self, input_file: Path, output_dir: Path) -> None:
        data = yaml.safe_load(input_file.read_text(encoding='utf-8'))
        unique_sets = self._extract_unique_sets(data)
        logger.info(f"Found {len(unique_sets)} unique sets")

        canonical_map = self.set_resolver.group_set_names(unique_sets)
        unique_sets = set(canonical_map.values())
        logger.info(f"Grouped into {len(unique_sets)} canonical sets")

        set_code_map = self._build_set_code_map(unique_sets)
        product_sets = self._process_products(data, canonical_map, set_code_map)

        output_dir.mkdir(parents=True, exist_ok=True)
        self._write_output_files(product_sets, output_dir)

    def _extract_unique_sets(self, data: Dict[str, Any]) -> set[str]:
        unique_sets = set()
        for provider, products in data.items():
            if not isinstance(products, dict):
                continue
            for product_name in products.keys():
                if set_name := self.set_resolver.extract_set_name(product_name):
                    unique_sets.add(set_name)
        return unique_sets

    def _build_set_code_map(self, unique_sets: set[str]) -> Dict[str, str]:
        set_code_map = {}
        for set_name in sorted(unique_sets):
            code = self.set_resolver.find_set_code(set_name)
            if not code or code.strip() == '':
                code = "unknown"
            set_code_map[set_name.lower()] = code

        logger.info("\nSet code mapping:")
        for name, code in sorted(set_code_map.items()):
            logger.info(f"  '{name}' -> '{code}'")
        return set_code_map

    def _process_products(
        self, data: Dict[str, Any], canonical_map: Dict[str, str], set_code_map: Dict[str, str]
    ) -> Dict[str, ReleaseSet]:
        product_sets: Dict[str, ReleaseSet] = {}
        failed_extractions = []

        for provider, products in data.items():
            if not isinstance(products, dict) or not provider or provider.strip() == '':
                continue

            for product_name, product_data in products.items():
                if 'Could not load provider' in product_name:
                    continue

                set_code = self._determine_set_code(
                    product_name, canonical_map, set_code_map, failed_extractions
                )

                if not set_code or set_code.strip() == '':
                    set_code = "unknown"

                category, subtype = self.categorize(product_name)

                product = Product(
                    language=product_data.get('language', 'en'),
                    category=category,
                    subtype=subtype,
                    identifiers=product_data.get('identifiers', {}).copy(),
                    release_date=product_data.get('release_date', ''),
                    purchase_url=PurchaseUrl()
                )

                if set_code not in product_sets:
                    product_sets[set_code] = ReleaseSet(code=set_code)

                product_sets[set_code].add_or_merge_product(product_name, product)

        if failed_extractions:
            logger.warning(f"\nFailed to extract set names from {len(failed_extractions)} products")

        return product_sets

    def _determine_set_code(
        self, product_name: str, canonical_map: Dict[str, str],
        set_code_map: Dict[str, str], failed_extractions: list
    ) -> str:
        if 'secret lair' in product_name.lower():
            return "sld"

        extracted = self.set_resolver.extract_set_name(product_name)
        if not extracted:
            failed_extractions.append(product_name)
            return "unknown"

        canonical = canonical_map.get(extracted, extracted)
        set_code = set_code_map.get(canonical.lower())

        if not set_code:
            return "unknown"

        return set_code

    def _write_output_files(self, product_sets: Dict[str, ReleaseSet], output_dir: Path) -> None:
        for set_code, product_set in product_sets.items():
            if not set_code or set_code.strip() == '':
                set_code = "UNKNOWN"

            product_set.code = set_code

            output_file = output_dir / f"{set_code.upper()}.yaml"

            if output_file.exists():
                try:
                    existing_set = ReleaseSet.from_yaml_file(output_file)
                    existing_set.code = set_code
                    for name, product in product_set.products.items():
                        existing_set.add_or_merge_product(name, product)
                    product_set = existing_set
                except Exception as e:
                    logger.error(f"Error loading existing file {output_file}: {e}")

            product_set.to_yaml_file(output_dir)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="MTG Product Categorizer (Free Version)")
    parser.add_argument("-i", "--input-file", type=Path, default=Path("./data/review.yaml"))
    parser.add_argument("-o", "--output-dir", type=Path, default=Path("./data/products"))
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    processor = ProductProcessor()
    processor.process(args.input_file, args.output_dir)


if __name__ == "__main__":
    main()

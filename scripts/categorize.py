import re
from typing import Dict, List, Optional, Tuple
from collections import Counter, defaultdict
from difflib import SequenceMatcher

CONFIDENCE_THRESHOLD = 0.65

SOHO_SEGMENTS = {
    'B': ('BOOSTER_PACK', 'DEFAULT'),
    'BEG': ('KIT', 'DEFAULT'),
    'BEGIN': ('KIT', 'DEFAULT'),
    'BUN': ('BUNDLE', 'DEFAULT'),
    'CB': ('BOOSTER_PACK', 'COLLECTOR'),
    'CHO': (None, None),  # Variant modifier
    'COM': ('DECK', 'COMMANDER'),
    'DB': ('BOOSTER_BOX', 'DRAFT'),
    'GEBUN': ('BUNDLE', 'GIFT_BUNDLE'),
    'HOL': (None, None),  # Variant modifier
    'JMP': ('BOOSTER_PACK', 'JUMPSTART'),
    'LS': ('KIT', 'LAND_STATION'),
    'PB': ('BOOSTER_PACK', 'PLAY'),
    'PR': ('LIMITED', 'PRERELEASE'),
    'SB': ('BOOSTER_PACK', 'SET'),
    'SCENE': ('BOX_SET', 'OTHER'),
    'SK': ('KIT', 'STARTER'),
    'STR': ('DECK', 'STARTER'),
}

LANGUAGE_MAP = {
    'JP': 'Japanese'
}


class FuzzyCategorizer:
    """Fuzzy matching and inference categorization"""
    
    def __init__(self):
        self.known_products: Dict[str, tuple[str, str]] = {}
        self.token_patterns: Dict[str, Counter] = defaultdict(Counter)
        
    def train(self, products: Dict[str, Dict]):
        """Train on known categorized products"""
        for name, data in products.items():
            cat = data.get("category")
            sub = data.get("subtype", "DEFAULT")
            if cat == "UNKNOWN":
                continue
                
            self.known_products[name.lower()] = (cat, sub)
            for token in self._tokenize(name):
                self.token_patterns[cat][token] += 1
                
    def categorize(self, name: str) -> tuple[str, str, float]:
        """Fuzzy categorize with confidence score"""
        name_lower = name.lower()
        tokens = self._tokenize(name)
        
        for known, (cat, sub) in self.known_products.items():
            ratio = SequenceMatcher(None, name_lower, known).ratio()
            if ratio >= 0.85:
                return (cat, sub, ratio)
        
        cat_scores = defaultdict(float)
        for token in tokens:
            for cat, counts in self.token_patterns.items():
                if token in counts:
                    cat_scores[cat] += counts[token] / sum(counts.values())
        
        if cat_scores:
            best_cat, score = max(cat_scores.items(), key=lambda x: x[1])
            confidence = score / len(tokens) if tokens else 0
            if confidence >= CONFIDENCE_THRESHOLD:
                return (best_cat, self._infer_subtype(tokens, best_cat), confidence)
        
        return ("UNKNOWN", "DEFAULT", 0.0)
    
    def _tokenize(self, name: str) -> List[str]:
        """Extract meaningful tokens"""
        clean = re.sub(r'[^\w\s\-]', ' ', name.lower())
        return [t for t in clean.split() if len(t) > 2 and t not in {'the', 'and', 'for', 'with', 'set', 'of'}]
    
    def _infer_subtype(self, tokens: List[str], category: str) -> str:
        """Infer subtype from tokens"""
        subtypes = {
            "BOOSTER_PACK": {"collector": "COLLECTOR", "play": "PLAY", "draft": "DRAFT", "premium": "PREMIUM"},
            "BOOSTER_BOX": {"collector": "COLLECTOR", "play": "PLAY", "draft": "DRAFT"},
            "DECK": {"commander": "COMMANDER", "theme": "THEME", "starter": "STARTER", "challenger": "CHALLENGER"},
            "BUNDLE": {"fat": "FAT_PACK", "gift": "GIFT_BUNDLE"},
            "LIMITED": {"prerelease": "PRERELEASE", "draft": "DRAFT"},
            "BOX_SET": {"secret": "SECRET_LAIR", "vault": "FROM_THE_VAULT", "spellbook": "SPELLBOOK"},
        }
        
        for token in tokens:
            for key, sub in subtypes.get(category, {}).items():
                if key in token:
                    return sub
        return "DEFAULT"


class ProductCategorizer:
    """Strict and fuzzy product categorization"""
    
    fuzzy: Optional[FuzzyCategorizer] = None
    
    RULES = [
        (["secret lair", "bundle"], "BOX_SET", "SECRET_LAIR_BUNDLE"),
        (["secret lair", "countdown"], "KIT", "SECRET_LAIR"),
        (["secret lair"], "BOX_SET", "SECRET_LAIR"),
        (["from the vault"], "BOX_SET", "FROM_THE_VAULT"),
        (["spellbook"], "BOX_SET", "SPELLBOOK"),
        (["commander collection"], "BOX_SET", "COMMANDER_COLLECTION"),
        (["commander anthology"], "BOX_SET", "DEFAULT"),
        (["game night"], "BOX_SET", "GAME_NIGHT"),
        (["anthology"], "BOX_SET", "DEFAULT"),
        
        (["case", "booster", "collector"], "BOOSTER_CASE", "COLLECTOR"),
        (["case", "booster", "play"], "BOOSTER_CASE", "PLAY"),
        (["case", "booster"], "BOOSTER_CASE", "DEFAULT"),
        (["case", "bundle"], "BUNDLE_CASE", "DEFAULT"),
        (["case", "commander"], "DECK_BOX", "COMMANDER"),
        (["master case"], "BOOSTER_CASE", "DEFAULT"),
        
        (["booster box", "collector"], "BOOSTER_BOX", "COLLECTOR"),
        (["booster box", "play"], "BOOSTER_BOX", "PLAY"),
        (["booster box", "draft"], "BOOSTER_BOX", "DRAFT"),
        (["booster display", "collector"], "BOOSTER_BOX", "COLLECTOR"),
        (["booster display", "play"], "BOOSTER_BOX", "PLAY"),
        (["booster display"], "BOOSTER_BOX", "DEFAULT"),
        (["booster box"], "BOOSTER_BOX", "DEFAULT"),
        
        (["booster", "collector", "!box", "!case", "!display"], "BOOSTER_PACK", "COLLECTOR"),
        (["booster", "play", "!box", "!case", "!display"], "BOOSTER_PACK", "PLAY"),
        (["booster", "draft", "!box", "!case", "!display"], "BOOSTER_PACK", "DRAFT"),
        (["booster", "set", "!box", "!case", "!display"], "BOOSTER_PACK", "SET"),
        (["booster", "theme", "!box", "!case", "!display"], "BOOSTER_PACK", "THEME"),
        (["booster", "jumpstart", "!box", "!case", "!display"], "BOOSTER_PACK", "JUMPSTART"),
        (["booster", "omega"], "BOOSTER_PACK", "PREMIUM"),
        (["booster", "sample"], "BOOSTER_PACK", "DEFAULT"),
        (["booster", "hanger"], "BOOSTER_PACK", "DEFAULT"),
        (["booster", "!box", "!case", "!display"], "BOOSTER_PACK", "DEFAULT"),
        
        (["fat pack", "!bundle"], "BUNDLE", "FAT_PACK"),
        (["bundle", "fat pack"], "BUNDLE", "FAT_PACK"),
        (["bundle", "gift"], "BUNDLE", "GIFT_BUNDLE"),
        (["bundle", "nightmare"], "BUNDLE", "DEFAULT"),
        (["bundle", "commanders"], "BUNDLE", "DEFAULT"),
        (["bundle", "pizza"], "BUNDLE", "DEFAULT"),
        (["bundle", "finish line"], "BUNDLE", "DEFAULT"),
        (["bundle"], "BUNDLE", "DEFAULT"),
        
        (["commander deck", "set of"], "MULTI_DECK", "COMMANDER"),
        (["commander decks", "set of"], "MULTI_DECK", "COMMANDER"),
        (["commander deck", "display"], "DECK_BOX", "COMMANDER"),
        (["commander deck", "carton"], "DECK_BOX", "COMMANDER"),
        (["commander deck"], "DECK", "COMMANDER"),
        (["commander:"], "DECK", "COMMANDER"),
        
        (["theme deck", "display"], "DECK_BOX", "THEME"),
        (["theme deck"], "DECK", "THEME"),
        (["60 card", "theme"], "DECK", "THEME"),
        (["60-card"], "DECK", "THEME"),
        (["planeswalker deck", "display"], "DECK_BOX", "PLANESWALKER"),
        (["planeswalker deck"], "DECK", "PLANESWALKER"),
        (["intro pack", "display"], "DECK_BOX", "INTRO"),
        (["intro pack"], "DECK", "INTRO"),
        (["starter deck", "display"], "DECK_BOX", "STARTER"),
        (["starter deck"], "DECK", "STARTER"),
        (["challenger deck", "display"], "DECK_BOX", "CHALLENGER"),
        (["challenger deck"], "DECK", "CHALLENGER"),
        (["duel deck"], "DECK", "DUEL"),
        (["welcome deck"], "DECK", "WELCOME"),
        (["brawl deck"], "DECK", "BRAWL"),
        (["event deck"], "DECK", "EVENT"),
        
        (["prerelease", "promo"], "BOOSTER_PACK", "PROMOTIONAL"),
        (["prerelease", "pack", "case"], "LIMITED", "PRERELEASE"),
        (["prerelease", "carton"], "LIMITED", "PRERELEASE"),
        (["prerelease", "pack"], "LIMITED", "PRERELEASE"),
        (["prerelease", "!pack"], "LIMITED", "PRERELEASE"),
        (["draft night", "case"], "LIMITED", "DRAFT"),
        (["draft night"], "LIMITED", "DRAFT"),
        
        (["scene box", "set"], "BOX_SET", "OTHER"),
        (["scene box", "case"], "BOX_SET", "OTHER"),
        (["scene box", "carton"], "BOX_SET", "OTHER"),
        (["scene box"], "BOX_SET", "OTHER"),
        
        (["box topper"], "BOOSTER_PACK", "TOPPER"),
        (["promo pack"], "BOOSTER_PACK", "PROMOTIONAL"),
        (["gift box"], "BOX", "GIFT_BUNDLE"),
        
        (["starter kit", "case"], "KIT", "DEFAULT"),
        (["starter kit"], "KIT", "STARTER"),
        (["deck builder"], "KIT", "DECK_BUILDERS_TOOLKIT"),
        (["land station"], "KIT", "LAND_STATION"),
        (["team-up", "case"], "KIT", "EVENT"),
        (["team up", "case"], "KIT", "EVENT"),
        (["team-up", "!case"], "KIT", "EVENT"),
        (["team up", "!case"], "KIT", "EVENT"),
        (["beginner box", "case"], "KIT", "DEFAULT"),
        (["beginner box"], "KIT", "DEFAULT"),
        (["kit"], "KIT", "DEFAULT"),
        
        (["tin"], "BOX", "DEFAULT"),
        (["display"], "DECK_BOX", "DEFAULT"),
    ]
    
    @classmethod
    def initialize_fuzzy(cls, known_products: Dict[str, Dict]):
        """Initialize fuzzy categorizer with training data"""
        cls.fuzzy = FuzzyCategorizer()
        cls.fuzzy.train(known_products)

    @classmethod
    def categorize(cls, name: str) -> tuple[str, str, float]:
        """Categorize product with confidence score"""
        name_lower = name.lower()
        
        for patterns, category, subtype in cls.RULES:
            required = [p for p in patterns if not p.startswith("!")]
            excluded = [p[1:] for p in patterns if p.startswith("!")]
            
            if all(p in name_lower for p in required) and not any(e in name_lower for e in excluded):
                return (category, subtype, 1.0)
        
        if cls.fuzzy:
            return cls.fuzzy.categorize(name)
        
        return ("UNKNOWN", "DEFAULT", 0.0)


def parse_item_number(item_number: str) -> Tuple[Optional[str], str, Optional[Tuple[str, str]]]:
    """Parse WCMG item number to extract release code, language, and product type hint"""
    
    if not item_number.startswith('WCMG'):
        return None, 'English', None
    
    remainder = item_number[4:]
    if len(remainder) < 3:
        return None, 'English', None
    
    release_code = remainder[:3]
    remainder = remainder[3:]
    
    language = 'English'
    language_segments = set(LANGUAGE_MAP.keys())
    product_segment_keys = set(SOHO_SEGMENTS.keys())
    
    i = 0
    while i < len(remainder) - 1:
        segment = remainder[i:i+2].upper()
        if segment in language_segments:
            before_ok = (i == 0 or remainder[i-1:i+2].upper() not in product_segment_keys)
            after_ok = (i + 2 >= len(remainder) or remainder[i:i+3].upper() not in product_segment_keys)
            
            if before_ok and after_ok:
                language = LANGUAGE_MAP[segment]
                break
        i += 1
    
    product_hint = None
    sorted_segments = sorted(product_segment_keys, key=len, reverse=True)
    
    for segment in sorted_segments:
        if segment in remainder.upper():
            category, subtype = SOHO_SEGMENTS[segment]
            if category:
                product_hint = (category, subtype)
                break
    
    return release_code, language, product_hint


def categorize_with_hints(name: str, item_number: str) -> Tuple[str, str, float]:
    """Categorize using both name and item number hints"""
    
    category, subtype, confidence = ProductCategorizer.categorize(name)
    
    if confidence < 0.8 or category == "UNKNOWN":
        _, _, product_hint = parse_item_number(item_number)
        
        if product_hint:
            hint_category, hint_subtype = product_hint
            
            if category == "UNKNOWN":
                return hint_category, hint_subtype, 0.7
            
            if confidence < 0.8:
                return hint_category, hint_subtype, 0.75
    
    return category, subtype, confidence
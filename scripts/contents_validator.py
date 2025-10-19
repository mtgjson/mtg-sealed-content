import yaml
import product_classes as pc
from pathlib import Path

valid_categories = [
    "BOOSTER_PACK", "BOOSTER_BOX", "BOOSTER_CASE", "DECK", "MULTI_DECK",
    "DECK_BOX", "BOX_SET", "KIT", "BUNDLE", "BUNDLE_CASE",
    "LIMITED", "LIMITED_CASE", "SUBSET"
]
old_categories = [
    "UNKNOWN", "CASE", "COMMANDER_DECK", "LAND_STATION", "TWO_PLAYER_STARTER_SET",
    "DRAFT_SET", "PRERELEASE_PACK", "PRERELEASE_CASE"
]
valid_subtypes = [
    "DEFAULT", "SET", "COLLECTOR", "JUMPSTART", "PROMOTIONAL", "THEME", "TOURNAMENT",
    "WELCOME", "TOPPER", "PLANESWALKER", "CHALLENGE", "EVENT", "CHAMPIONSHIP",
    "INTRO", "COMMANDER", "BRAWL", "ARCHENEMY", "PLANECHASE", "STARTER", "DRAFT_SET",
    "TWO_PLAYER_STARTER", "DUEL", "CLASH", "BATTLE", "GAME_NIGHT", "FROM_THE_VAULT",
    "SPELLBOOK", "SECRET_LAIR", "SECRET_LAIR_BUNDLE", "COMMANDER_COLLECTION",
    "COLLECTORS_EDITION", "GUILD_KIT", "DECK_BUILDERS_TOOLKIT", "LAND_STATION",
    "GIFT_BUNDLE", "FAT_PACK", "MINIMAL", "PREMIUM", "ADVANCED", "DRAFT", "PLAY",
    "SEALED_SET", "PRERELEASE", "OTHER", "CHALLENGER", "SIX", "CONVENTION", "REDEMPTION"
]

if __name__ == "__main__":
    contentFolder = Path("data/contents/")
    failed = False
    for set_file in contentFolder.glob("*.yaml"):
        with open(set_file, "rb") as f:
            contents = yaml.safe_load(f)

        for name, p in contents["products"].items():
            if not p:
                p = {}
            if isinstance(p, list):
                print(f"Product {name} in set {set_file.stem} formatted incorrectly")
                failed = True
                continue
            if set(p.keys()) == {"copy"}:
                p = contents["products"][p["copy"]]
            try:
                pc.product(p, contents["code"], name)
            except:
                print(f"Product {name} in set {set_file.stem} failed")
                failed = True
    if failed:
        raise ImportError()

    productsFolder = Path("data/products/")
    failed = False
    all_files = sorted(list(productsFolder.glob("*.yaml")))
    for set_file in all_files:
        with open(set_file, "rb") as f:
            contents = yaml.safe_load(f)
        
        for name, p in contents["products"].items():
            if "category" not in p.keys():
                print(f"Product {name} in set {set_file.stem} missing category")
                failed = True
            elif p['category'] not in valid_categories:
                if p['category'] in old_categories:
                    print(f"Product {name} uses an old category")
                    #pass
                else:
                    print(f"Product {name} has an invalid category: {p['category']}")
                    failed = True
            if "subtype" not in p.keys():
                print(f"Product {name} in set {set_file.stem} missing subtype")
                failed = True
            elif p['subtype'] not in valid_subtypes:
                if p['subtype'] == "UNKNOWN":
                    print(f"Product {name} missing a valid subtype")
                    #pass
                else:
                    print(f"Product {name} uses an invalid subtype: {p['subtype']}")
                    failed = True
    if failed:
        raise ImportError()
    print("All products validated")

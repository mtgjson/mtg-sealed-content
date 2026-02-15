# mtg-sealed-contents
Repository that collects all sealed MTG products and maps their contents.

## How it works

The goal of this project is to catalogue each Magic: The Gathering product and their contents.

Most of the data is loaded from upstream, using taw's repositories, [magic-search-engine](https://github.com/taw/magic-search-engine/) and [magic-preconstructed-decks](https://github.com/taw/magic-preconstructed-decks/), often automatically through Github Actions. This data is then validated and rebuilt in a JSON file, and inserted in MTGJSON daily builds, it strictly has to adhere to MTGJSON coding styles and conventions.

Thanks to a series of scripts we're able to
- load new decks from taw automatically
- map the contents of each deck and booster to physical cards
- map products to third-party marketplaces
- keep track of various bonus cards and obscure products
- keep track of what the repository is missing

This is a massive undertaking of course, so any help and contribution to improve coverage is welcome! If you don't know where to start, keep reading and check the `data/review.yaml` file for suggestions.

## Getting Started

### Prerequisites

- Python 3.x and a working virtual environment
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- (optional) Recent version of AllPrintings.json file

### Repository Structure


```
data/products/  # YAML files defining sealed product
data/contents/  # YAML files describing sealed product contents
scripts/        # Python scripts for compiling YAML → JSON
outputs/        # Generated JSON output (do not edit directly)
.github/        # GitHub Actions workflows
```

The main difference between `products` and `contents` is that the first defines the product itself, with a list of identifiers, category (deck, booster, box, etc) and subtype (collector booster, draft booster, prerelease and so on), while the second contains the description of the contents themselves, i.e. what users will find should they open the product (i.e. they will find 6 Booster Boxes in a Case).

## Contributing

### Adding Sealed Product Data

If you want to add a new sealed product or complete a product description you will need to modify both the product description and product definition files. You can insert the new entries anywhere in the file, as they will be kept sorted by the daily scripts.

For example, assuming you want to add a completely new product, you need to add a product entry to `data/products/SETCODE.yaml`, and a product description to `data/contents/SETCODE.yaml`. Products are defined with a basic `category`, `identifiers`, and `subtype` structure, while they are described using the content types documented below: `card`, `pack`, `deck`, `sealed`, `variable`, and `other`.


- `data/products/SETCODE.yaml`
```yaml
  My Set Booster Box:
    category: BOOSTER
    identifiers:
    - markeptlace: 1234
    subtype: DRAFT
```

- `data/products/SETCODE.yaml`
```yaml
  My Set Booster Box:
    sealed:
    - count: 30
      name: My Set Set Booster Pack
      set: mysetcode
```

### Mapping product identifiers

Data from marketplaces is loaded every day and stored in `data/review.yaml` though `scripts/load_new_products.py`.

This file is then manually processed with `scripts/check_product_fuzzy.py` which maps a product id to each product defined, using fuzz matching, or create a new product entirely on the fly. This script will provide an interactive shell with a list of possible matches, as well as possible extra options in case the product does not end up being listed.

Example output:

```
Finding similar products for Chaos Vault - Adventures of the Little Witch - Foil {'cardKingdomId': '313132'}
  0 - Secret Lair Drop Adventures of the Little Witch
  1 - Secret Lair Drop Adventures of the Little Witch Rainbow Foil
  2 - Adventures in the Forgotten Realms Theme Booster White
  3 - Adventures in the Forgotten Realms Set Booster Box
  4 - Adventures in the Forgotten Realms Theme Booster Set of 6
Select action ('h' for help):
```

The available actions are:
- `q` - quit the script cleanly
- `s` - skip this product and leave it unreviewed
- `i` - ignore this product and never prompt it again
- `m` - list more possible matches
- `b` - go back to the possible matches
- `u` - undo the previous action and go the previous entry
- `c` - create a new product
- `0`/`1`/`2`/`3`/`4` - pick the product entry (0 is default)
- use the exact name of the product to add the id

For the example above, the right keypress would be `1`.

### Defining card drop rates and probabilities

For simple random cards found in various products it is possible to define a minimal drop rate configuration, but this should be used only for specific product lines (i.e. Secret Lair bonus cards). See below for an example use case.

More generally, booster drop rates, EV, and pull probability are not tracked by this project. Please check out [magic-search-engine](https://github.com/taw/magic-search-engine/).

### Adding decks

A small amount of cards can be defined through the `card` tag, but the list shouldn't exceed 4-5 entries.

Full decklists are not tracked by this project. Please check out [magic-preconstructed-decks](https://github.com/taw/magic-preconstructed-decks/).

### Automations

A lot of scripts are run every day, through Github Actions, with the goal of pulling and associating as much data as possible automatically to minimize the chances of human errors.

- New decks, including SLD drops, are pulled from upstream and added through `scripts/import_new_decks.py`
- Card-to-product mapping is generated from `scripts/card_to_product_compiler.py` using a recent MTGJSON version
- New product ids are pulled from `scripts/load_new_products.py`

## Categories and Subtypes

These two fields in product descriptions define the type of sealed product for ease of cataloguing. The main difference between them is that the former define the type (i.e. Pack, Deck etc) within the same set, and the latter defines the higher level series (i.e. Jumpstart, Commander, Secret Lair) across multiple sets.

The most straightforward example is for Booster Packs: the **category** should intuitively be set to `BOOSTER_PACK`, and the **subtype** should be set to `DRAFT`, `PLAY`, `SET`, `COLLECTOR` depending on the product.

Using UNKNOWN/DEFAULT works too, but it's better to be as accurate as possible when adding new sets.

### Categories

| Name | Description |
|------|-------------|
| `BOOSTER_PACK` | A single sealed pack containing a randomized assortment of cards |
| `BOOSTER_BOX` | A box containing multiple booster packs |
| `BOOSTER_CASE` | A sealed case containing multiple booster boxes |
| `DECK` | A pre-constructed, ready-to-play deck, usually distributed in larger displays (i.e. theme decks) |
| `DECK_BOX` | A pre-constructed, ready-to-play deck, usually distributed in small displays (i.e. commander decks) |
| `MULTI_DECK` | A product containing two or more pre-constructed decks |
| `BOX_SET` | A particular product containing a set amount of cards, sometimes with extra promotional material |
| `KIT` | A themed package with cards and materials, often for learning or events |
| `BUNDLE` | A combined product with multiple items (e.g., packs, promos, accessories) |
| `BUNDLE_CASE` | A sealed case containing multiple bundles |
| `LIMITED` | A limited-edition or exclusive release product (i.e. prerelease products) |
| `LIMITED_CASE` | A sealed case containing multiple limited-edition products |
| `SUBSET` | A product combining other products (i.e. two specific decks) |

### Subtypes

| Name | Description |
|------|-------------|
| `DEFAULT` | The standard or default product type when no specific category applies |
| `SET` | A booster or product from the Set series, usually containing a card from *The List* |
| `COLLECTOR` | A premium booster or product with enhanced card treatments and rarities |
| `JUMPSTART` | A product designed for the *Jumpstart* format, combining two half-decks into one |
| `PROMOTIONAL` | A product containing promotional or limited-distribution cards |
| `THEME` | A themed product built around a specific mechanic, color, or concept |
| `TOURNAMENT` | A product designed for or distributed at organized tournament play |
| `WELCOME` | An introductory product given to new players to learn the game |
| `TOPPER` | A special bonus card or mini-pack included on top of a booster box |
| `PLANESWALKER` | A pre-constructed deck centered around a specific Planeswalker character |
| `CHALLENGE` | A product from the *Challenge a God* series |
| `EVENT` | A product tied to a specific in-store or organized play event |
| `CHAMPIONSHIP` | A product associated with championship-level tournaments or winners |
| `INTRO` | An introductory pre-constructed deck for beginner players |
| `COMMANDER` | A pre-constructed deck designed for the *Commander* format |
| `BRAWL` | A pre-constructed deck designed for the Brawl format |
| `ARCHENEMY` | A product designed for the *Archenemy* multiplayer format |
| `PLANECHASE` | A product designed for the *Planechase* multiplayer format |
| `STARTER` | A beginner-friendly starter product with everything needed to start playing |
| `DRAFT_SET` | A set or product specifically curated for draft-format play |
| `TWO_PLAYER_STARTER` | A starter product designed for two players to learn and play together |
| `DUEL` | A product from the *Duel Decks* series |
| `CLASH` | A product from the *Battle Clash* series |
| `BATTLE` | A product centered on battle or combat-themed gameplay |
| `GAME_NIGHT` | A multiplayer box set designed for casual game night sessions |
| `FROM_THE_VAULT` | A premium boxed set featuring reprints of iconic cards with special treatments |
| `SPELLBOOK` | A themed collection of reprinted cards with alternate art in a premium package |
| `SECRET_LAIR` | A limited-edition drop with uniquely styled cards, sold directly to consumers |
| `SECRET_LAIR_BUNDLE` | A bundle containing multiple *Secret Lair* drops |
| `COMMANDER_COLLECTION` | A product from the *Commander Collection* series |
| `COLLECTORS_EDITION` | A premium product aimed at collectors with special finishes or exclusive cards |
| `GUILD_KIT` | A themed deck built around a specific guild |
| `DECK_BUILDERS_TOOLKIT` | A starter product with cards, lands, and packs to help build custom decks |
| `LAND_STATION` | A box containing a large supply of basic land cards for events or deck building |
| `GIFT_BUNDLE` | A bundle packaged as a gift, typically with extra items like dice or promos |
| `FAT_PACK` | An older term for a bundle containing booster packs, lands, and a storage box |
| `MINIMAL` | A commander deck packaged in a basic cardboard box |
| `PREMIUM` | A higher-tier product featuring foil, alternate art, or enhanced materials |
| `ADVANCED` | A product designed for experienced or competitive players |
| `DRAFT` | A booster product used for drafting |
| `PLAY` | A booster product used for playing or drafting |
| `SEALED_SET` | A complete sealed set of cards from a specific release |
| `PRERELEASE` | A special product distributed at prerelease events before official launch |
| `OTHER` | A catch-all category for products that don't fit other classifications |
| `CHALLENGER` | A pre-constructed product from the *Challenger Decks* series |
| `SIX` | A product designed for the six-card or six-player format |
| `CONVENTION` | An exclusive product available only at conventions or special events |
| `REDEMPTION` | A product obtained through Magic Online Redemption Program |

## Product contents

Product sealed contents use the following types: `card`, `pack`, `deck`, `sealed`, `variable`, and `other`.

### `card`

A `card` object refers to a single card, usually a promotional card.

`card` objects have the following properties:

```
name: [str] Full card name
set: [str] Set code
number: [str or int] Collector number
foil: [bool, optional] True if card is traditional or etched foil
uuid: [str, calculated] The card's MTGJson UUID. This is calculated by the compiler and you should not enter this in the YAML.
```

Example card YAML input:

```yaml
  Phyrexia All Will Be One Compleat Bundle:
    card:
    - set: one
      name: Phyrexian Arena
      number: 283
      foil: true
  ...
```

JSON result:

```json
"contents": {
    "card": [
        {
            "foil": true, 
            "name": "Phyrexian Arena", 
            "number": "283", 
            "set": "one", 
            "uuid": "dab29a67-28a9-5847-a77e-1f0771b55be1"
        }
    ],
    "...": []
}
```

### `pack`

A `pack` object refers to an existing object in MTGJson `{set}.booster`. When `pack` is included in the product contents, the `card_count` parameter is required.

`pack` objects have the following properties:

```
set: [str] Set code
code: [str] Internal reference code targeting {set}.booster. 'default' refers to the draft booster for a given set.
```

Example pack YAML input:

```yaml
  Unlimited Edition Booster Pack:
    pack:
    - set: 2ed
      code: default
```

JSON result:

```json
"contents": {
    "pack": [
        {
            "code": "default", 
            "set": "2ed"
        }
    ]
}
```

### `deck`

A `deck` object refers to a precompiled deck object. When `deck` is included in the product contents, the `card_count` parameter is required.

`deck` objects have the following properties:

```
set: [str] Set code
name: [str] The deck's name matching its MTGJson object.
```

Example deck YAML input:

```yaml
  7th Edition Theme Deck Armada:
    deck:
    - set: 7ed
      name: Armada
```

JSON result:

```json
"contents": {
    "deck": [
        {
            "name": "Armada",
            "set": "7ed"
        }
    ]
}
```

### `sealed`

A `sealed` object refers to another sealed object. 

`sealed` objects have the following properties:

```
set: [str] Set code
name: [str] The product name
count: [int] Count of included products
uuid: [str, calculated] The MTGJson UUID of the linked product. This is calculated by the compiler and should not be added in the YAML.
```

Example sealed YAML input:

```yaml
  Unlimited Edition Booster Box:
    sealed:
    - count: 36
      name: Unlimited Edition Booster Pack
      set: 2ed
```

JSON result:

```json
"contents": {
    "sealed": [
        {
            "count": 36,
            "name": "Unlimited Booster Pack",
            "set": "2ed",
            "uuid": "3f7ddeba-52f5-5f8f-a013-309403c8a870"
        }
    ]
}
```

### `variable`

A `variable` object contains a list of possible contents for the product.

`variable` products are defined in two sections: the main `variable` key and the `variable_mode` key.

The `variable` key defines all the possible sub-components to be chosen from randomly.

The `variable_mode` key defines how the components will be randomized.

`variable` objects have the following properties:

```
configs: [list[object]] A list of the possible configuration objects
```

`variable_mode` objects have the following properties:

```
count: [int] The number of components to pull
replacement: [bool] Whether duplicates are allowed in the randomization
```

Example variable YAML input:

```yaml
  Amonkhet Booster Battle Pack:
    card_count: 60
    sealed:
    - count: 2
      name: Amonkhet Booster Pack
      set: akh
    variable:
    - deck:
      - name: Amonkhet Welcome Deck - White
        set: w17
    - deck:
      - name: Amonkhet Welcome Deck - Blue
        set: w17
    - deck:
      - name: Amonkhet Welcome Deck - Black
        set: w17
    - deck:
      - name: Amonkhet Welcome Deck - Red
        set: w17
    - deck:
      - name: Amonkhet Welcome Deck - Green
        set: w17
    variable_mode:
      count: 2
      replacement: false
```

JSON result:

```json
"contents": {
    "sealed": [
        {
            "count": 2,
            "name": "Amonkhet Booster Pack",
            "set": "akh",
            "uuid": "bdfaa43d-9ebd-502f-856b-11eadc97b026"
        }
    ], 
    "variable": [
        {
            "configs": [
                {
                    "deck": [
                        {
                            "name": "Amonkhet Welcome Deck - White",
                            "set": "w17"
                        }, 
                        {
                            "name": "Amonkhet Welcome Deck - Blue",
                            "set": "w17"
                        }
                    ]
                }, 
                {
                    "deck": [
                        {
                            "name": "Amonkhet Welcome Deck - White",
                            "set": "w17"
                        },
                        {
                            "name": "Amonkhet Welcome Deck - Black",
                            "set": "w17"
                        }
                    ]
                },
                {"...": ""}
            ]
        }
    ]
}
```

### `other`

An `other` object refers to things not included in MTGJson. 

`other` objects have the following property:

`name: [str] A string describing the object`

Example other YAML input:

```yaml
  Unlimited Edition Starter Deck:
    pack:
    - set: 2ed
      code: starter
    other:
    - name: Unlimited Edition Starter Deck Rulebook
```

JSON result:

```json
"contents": {
    "other": [
        {
            "name": "Unlimited Edition Starter Deck Rulebook"
        }
    ],
    "pack": [
        {
            "code": "starter",
            "set": "2ed"
        }
    ]
}
```

## License

By contributing to this repository, you agree that your contributions will be licensed under the [MIT License](LICENSE.txt).

# mtg-sealed-contents
Repository that collects all sealed MTG products and maps their contents

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

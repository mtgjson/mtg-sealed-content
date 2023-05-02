# mtg-sealed-contents
Repository that collects all sealed MTG products and maps their contents

## Product contents

Product sealed contents use the following types:

### `pack`

A `pack` object refers to an existing object in MTGJson `{set}.booster`. Example pack:

```yaml
  Unlimited Edition Booster Pack:
    pack:
    - set: 2ed
      code: default
```

### `deck`

A `deck` object refers to a precompiled deck object. Example deck:

```yaml
  7th Edition Theme Deck Armada:
    deck:
    - set: 7ed
      name: Armada
```

### `sealed`

A `sealed` object refers to another sealed object. Sealed objects have a `count` associated with them. Example sealed:

```yaml
  Unlimited Edition Booster Box:
    sealed:
    - count: 36
      name: Unlimited Edition Booster Pack
      set: 2ed
```

### `variable`

A `variable` object contains a list of sub-contents. Example variable:

```yaml
  Phyrexia All Will Be One Jumpstart Booster Pack:
    variable:
    - deck:
      - set: one
        name: Mite-y 1
    - deck:
      - set: one
        name: Mite-y 2
  ...
```

### `card`

A `card` object refers to a single card (usually a promo). Example card:

```yaml
  Phyrexia All Will Be One Compleat Bundle
    sealed:
    - set: one
      name: Phyrexia All Will Be One Set Booster Pack
      count: 12
    card:
    - set: one
      name: Phyrexian Arena
      number: 283
      foil: true
  ...
```

### `other`

An `other` object refers to things not included in MTGJson. Example other:

```yaml
  Unlimited Edition Starter Deck:
    pack:
    - set: 2ed
      code: starter
    other:
    - name: Unlimited Edition Starter Deck Rulebook
```

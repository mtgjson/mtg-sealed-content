# Evidence and validation details

## Source pitfalls worth remembering

- [Magic Librarities bonus checklist](https://www.magiclibrarities.net/1299-rarities-secret-lair-drop-series-promos-english-cards-index.html) provides useful per-drop lists but includes errors and incomplete sections. A later occurrence does not make a printing exclusive to that drop.
- [Summer 2020 opening compilation](https://www.reddit.com/r/mtgfinance/comments/ih6h2e/stained_glass_planeswalkers_in_summer_secret_lair/) distinguishes reported outcomes from hypotheses. Its reported counts are self-selected, not unbiased pull-rate measurements.
- [Theros Erebos opening reports](https://www.reddit.com/r/mtgfinance/comments/f7d7qe/psa_liliana_confirmed_in_the_erebos_secret_lair/) and [additional reports](https://www.reddit.com/r/mtgfinance/comments/f67grh/) place Ashiok 528 in Erebos. The Librarities/Wiki tables placed it in Purphoros instead. The agreed correction preserves the established 11 red Purphoros outcomes and retains Ashiok in Erebos, with an explicit source override. One apparent column error did not justify discarding the supported Purphoros pool. This example is not permission to infer every drop's pool from color.
- Lair Tracker and similar lists can omit ordinary outcomes while listing rare replacements. Verify completeness before treating a page as the whole slot.
- The actual collector subreddit is `r/secretlair_collectors`. General explanations of bonus systems are leads, not historical drop-specific membership or rates.

## Complete bonus-slot example

This illustrates schema only; collector numbers and weights below are hypothetical. Read existing definitions and current compiler semantics before writing new packs.

```yaml
# Equal within-category weights and replacement odds are estimates.
# Record actual source URLs and assumptions here.
name: SLD Example Drop Bonus
pack:
  bonus: 1
sheets:
  bonus:
    foil: true
    any:
    - rawquery: e:{set} number:1001,1002
      count: 2
      chance: 95
    - rawquery: e:{set} number:1003
      count: 1
      chance: 5
```

The regular category has probability 95%, divided between its two cards; each is 47.5%, not 95%. Both categories compete for one slot. A single uniform pool needs only `rawquery`, `count` and finish metadata, without `any`.

The sealed consumer uses:

```yaml
pack:
- code: bonus-example-drop
  set: sld
```

`blueprint-mk1` by itself is a replacement catalog, not a complete bonus slot unless that product guarantees such a card. Do not reference any code without checking its definition and eligible membership.

## Validation gates

Use the current [general validation recipes](../../mtg-sealed-product-audit/references/validation.md) for runtime/compiler commands; discover installed runtimes rather than copying old temporary paths.

1. Compile every changed/new booster with the actual search-engine compiler and fresh index. Assert exact collector-number membership, physical finishes, intended cards per opening, normalized category/per-card probabilities, and absence of specifically excluded outcomes. Successful YAML parsing alone is insufficient.
2. Resolve every effective sealed pack reference, following copies and nested alternatives, against those compiled definitions. Check the whole repository for consumers of deleted codes. Keep deck lists, card counts, accessories and unrelated fixed cards unchanged unless independently justified.
3. Run the sealed contents validator. It can rewrite `status.txt`; exclude that and generated indexes/outputs from source commits. Distinguish unrelated existing warnings from failures.
4. For bonus-finish changes, check catalog-supported finishes and trace the actual output path. `etched: true` is distinct from `foil: true`; deck `isEtched` is a separate path. Check source card serialization, typed models, direct and variable contents, dataframe assembly where used, and card-to-product mapping. A schema accepting the key does not prove downstream propagation.
5. In `mtg-sealed-content`, inspect `scripts/product_classes.py` and `scripts/card_to_product_compiler.py`. If downstream output matters, also inspect fresh `mtgjson/mtgjson` models and `pipeline/stages/sealed.py`. Its duplicated mapper/model historically discarded etched or inferred nonfoil. Check current code instead of assuming an earlier PR merged or published. For direct-card flags, etched takes precedence over foil.
6. Use focused regression tests for actual propagation-code fixes; data-only edits usually need ephemeral compilation/invariant checks rather than new implementation-mirroring tests. Report if a full downstream rebuild was not performed. Previously computed outputs need regeneration; a source fix does not retroactively rewrite them.

Avoid storing static audit progress, current PR numbers, local scratch paths, or temporary pool inventories in this skill. Keep source-linked membership tables and year-specific unresolved work with the audit artifacts/issues.

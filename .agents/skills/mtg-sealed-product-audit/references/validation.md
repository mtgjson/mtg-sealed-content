# Validation recipes

Use the repositories' documented dependency environments. The inventory helper requires Python 3 and PyYAML; deck and booster validation require their Ruby dependencies and generated card data. Verify the selected interpreter after changing PATH. Git LFS may need access to the shared repository's cache even from an isolated worktree.

## Inventory

From the sealed worktree, after exporting decks:

```sh
python3 .agents/skills/mtg-sealed-product-audit/scripts/inventory.py \
  --sealed . \
  --search /path/to/magic-search-engine-worktree \
  --decks-json /tmp/audit-decks.json \
  --year 2025 \
  --output /tmp/audit-inventory.json
```

Replace the year and paths with the current audit scope. Repeat `--include-set CODE` to include a set outside the date selection. The helper only reads source data and writes the requested report; findings require manual verification.

## Decks

From the isolated deck worktree:

```
ruby bin/build_jsons /tmp/audit-decks.json
ruby bin/validate_card_names
```

Use the repository's dependency environment. `build_jsons` requires an output argument; without it, it validates but saves nothing. Export contains `set_code`, `name`, `release_date` and `cards` keyed by section. Inspect all gameplay sections and preserve display/token distinctions.

## Sealed

```
python3 scripts/contents_validator.py
git diff --check -- data/contents/SET.yaml
```

The validator may emit pre-existing category/subtype warnings and rewrite `status.txt`; retain its output and distinguish success from warnings. It does not prove that a deck/booster reference resolves upstream. Check the new references against fresh exports separately. Don't stage the generated status/output files.

## Booster compilation

From the search worktree, with the `search-engine/Gemfile` dependency environment:

```ruby
require_relative 'search-engine/lib/card_database'
require_relative 'booster_indexer/lib/booster_indexer'
db = CardDatabase.load
indexer = BoosterIndexer.new
indexer.load_data
code = 'hob-prerelease' # replace with target
set_code, pack_code = code.split('-', 2)
data = PreprocessBooster.new(indexer, code, YAML.load_file("data/boosters/#{code}.yaml")).call
pack = PackFactory.new(db, db.sets.fetch(set_code), pack_code || 'default', data).build_pack
puts pack.cards.size
```

Inspect physical card finishes and compare pool membership; `db.search(...).printings` can contain both faces while compiled packs count physical cards. A successful compilation is not evidence that an inferred probability is official.

## PRs

Inspect remotes before pushing: origin may be upstream read-only, while a `github` remote points to the user's writable fork. Use explicit default bases and body files with real newlines. Keep the description about the final implementation, validation and dependencies.

Useful 2026 examples (historical evidence, not current status):
- Decks #307 / sealed #541: tutorial/Commander collector numbers and separate Marvel Bundle/Gift Bundle lands.
- Sealed #542–544: missing prerelease boosters, Draft Night land references, accessories and case quantities.
- Decks #311 / search #562 / sealed #545: 34-land Hobbit bundles, fixed promo, four seasonal Plains and topper links.
- Sealed #546: ten land cards confused with five distinct names.

Known deferred example: Miku decklist was published but many stamped source printings were absent from the inspected index. Recheck before reusing that finding; don't treat its historical missing count as current.

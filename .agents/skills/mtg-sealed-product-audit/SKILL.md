---
name: mtg-sealed-product-audit
description: Audit Magic sealed products against Wizards collecting guides and trace missing card mappings across mtg-sealed-content, magic-preconstructed-decks, and magic-search-engine. Use for annual release audits, productless-card investigations, and product-content corrections.
---

# MTG sealed product audit

Compare physical product contents with the three source layers; distinguish wrong source data from missing upstream printings and delayed downstream publication. Scope can be one release or a release year. An audit request authorizes investigation; use existing conversation authorization when deciding whether to send fixes as PRs. Do not silently expand an annual audit into unrelated tooling changes.

## Source layers

- `mtgjson/mtg-sealed-content` (`main`): `data/products/SET.yaml` defines products/identifiers; `data/contents/SET.yaml` describes cards, decks, packs, nested sealed products and accessories.
- `taw/magic-preconstructed-decks` (`master`): `data/<type>/<set>/<deck>.txt` is canonical deck data. `bin/build_jsons <output>` exports sectioned deck JSON. `lib/deck_types.yaml` constrains permitted counts.
- `taw/magic-search-engine` (`master`): `data/boosters/<set>[-<pack>].yaml` defines booster slots/queries; `index/sets.json` supplies set dates; the card index resolves printings and finishes.
- MTGBAN productless search is a downstream symptom, not authoritative evidence that source data is missing.

Use isolated worktrees and fresh origin default-branch tips in every touched repository. Follow local checkout instructions: never switch or reset the user's checkout. If its checked-out default cannot safely be fast-forwarded, leave it untouched, use the fresh origin tip in an isolated worktree and disclose the distinction. Do not measure a stale feature branch. Target each PR at its repository's default branch, never another PR. Stage only intentional source files: the sealed validator can rewrite `status.txt`, and LFS/generated outputs are unrelated to content edits.

## Inventory and evidence

1. Determine the requested year/releases and exclusions from the conversation. Promo Packs, unreleased sets, accessories, and Secret Lair drops are scope decisions, not automatic exclusions. If the user excludes deck boxes, preserve existing entries and omit newly proposed ones.
2. Export current decks. Run `scripts/inventory.py` with the three worktree paths, deck JSON and year. The helper inventories date-selected products and checks empty content, unresolved references, copy cycles and deck-count discrepancies. It reports candidates, not defects.
3. Augment date-based inventory with products in official guides: supplemental sets may be absent from the set index, and new products can use an older set code. Explicit product release dates take precedence over inherited set dates. Report cases/bundles separately from unique standalone product types. Do not call the inventory exhaustive when undated SKUs or retailer exclusives remain unreviewed.
4. Read each guide's full product sections, not search snippets. Verify HTML extraction reaches the product details: selecting only the first `<article>` can truncate multi-section Wizards pages (observed with Innistrad Remastered). Usual URL: `https://magic.wizards.com/en/news/feature/collecting-<release>`. Search when the slug differs. First-look articles can be updated in place. Use official decklists, product pages or WPN pages for missing details. Retailer listings/unboxings can corroborate case quantities and exact printing/finish questions; label the evidence level.
5. Compare boosters per box, boxes per case, fixed promos versus random pools, decks, land packs, finish variants, tokens/art cards and accessories. A land list in `other` contributes no mapped cards. An existing top-level topper product still needs a reference from each eligible box.

## Card mapping decisions

- Welcome Deck boxes may contain one fixed half-deck plus a second random half-deck of another color. A correct single half-deck list does not describe the whole sealed product. Model the random choice at the deck level, preserving card correlations.
- Check set code, collector number, finish and product family together. A scene in a booster is not necessarily a Scene Box scene. Commander/deck, Jumpstart, tutorial and booster printings can share names but differ in numbers.
- Distinguish fixed Bundle promos from variable pools. A missing `bundle-promo` definition does not prove there is a random pack: directly map a known single card.
- Different bundles may share a promo but have different land lists. Verify traditional foil versus surge/etched variants; the deck syntax may encode special finishes via a separate collector number plus `[foil]`.
- Don't infer exact art distribution from a total such as “30 lands.” Use identified printings where verified. Default-frame `SET:*` round-robin selectors and evenly split Draft Night basics are existing conventions, not proof of physical collation; disclose assumptions. Don't silently extend a convention to special-art lands.
- Read repeated bullets in context. Seek corroboration before interpreting a duplicated seasonal-land bullet as twice as many cards.
- Store fixed lands in a deck list or direct `card` entries. A new legitimate land-pack size may require a narrow addition to the deck-type validator.
- Do not force every `card_count` to the sum of a deck: mixed products historically use inconsistent conventions; separately count fixed cards, randomized packs, nested sealed contents and bonus cards. Display commanders and ordinary tokens are not gameplay count. Some products (e.g. TMNT Enemy Deck) intentionally use token-typed gameplay cards and must not be reduced to zero.
- A published decklist may still lack exact stamped reprints in the card index. Match official original-printing tables against the correct stamped set, not the unstamped original. Separate unresolved references from confirmed absences; normalize split/double-faced names and front/back identity before counting. If exact printings remain unavailable, report the dependency instead of substituting wrong cards.

## Validation and delivery

Read [references/validation.md](references/validation.md) for concrete commands when validating changes.

Compile relevant existing boosters against the fresh index. Compilation verifies query counts/pools, not all slot odds or correlations. Only add rates supported by published data or explicitly identified repository conventions. Count physical front/back pairs as one card.

For fixes, export decks, validate metadata/card names, validate sealed YAML and check cross-references against the companion export. Assert meaningful invariants: total cards, foil/nonfoil split, excluded wrong printings, fixed seasonal variants, correct nested product counts. Review the final diff for unrelated regenerated files.

Work one release at a time when requested. Open separate PRs per affected repository and link cross-repository dependencies; describe what must propagate before the sealed build can resolve new references. Don't assume the user saying “merged” means every companion repository merged: fetch and verify.

Deliver a sourced report by release: confirmed fixes, unresolved evidence, upstream-data dependencies, and skipped scope. Include inventory/check limits. If MTGBAN still lists cards already fixed on current defaults, check publication/rebuild state before proposing duplicate fixes. Productless pages may cap at 100; do not report that cap as a total.

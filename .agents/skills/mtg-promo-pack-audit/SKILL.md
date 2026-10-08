---
name: mtg-promo-pack-audit
description: Create and audit seasonal WPN Promo Pack products and booster pools across mtg-sealed-content and magic-search-engine using Wizards contents lists. Use for new seasons, foil pool differences, or unmapped promo:promopack printings; not Secret Lair bonuses or Standard Showdown packs.
---

# WPN Promo Pack creation and coverage

Model each season's actual slots and exact printings, then connect regular and foil
products to those boosters. Read the [seasonal research ledger](../../../data/notes/wpn-promo-packs.md)
for existing sources, exceptions and unresolved interpretations before editing.
Keep historical findings there rather than duplicating the season inventory here.
For broader product work, use the [sealed-product audit](../mtg-sealed-product-audit/SKILL.md).

## Scope and working state

Use fresh default-branch tips and isolated worktrees in both repositories, following
local checkout instructions. Preserve the user's checkout if its checked-out default
cannot safely be advanced. Check existing PR state before pushing: the user may
have merged a companion PR during research. Never update a merged PR or stack PR
bases. This skill does not itself authorize publication.

For a requested full pass, continue season by season without stopping for approval
between routine items. Record unresolved questions while completing independent
work. A missing source is not permission to guess a pool merely to reach zero
unmapped cards. Distinguish a full coverage audit from adding one requested season.

## Establish the season and source

- Start at the [official set archive](https://magic.wizards.com/en/products/card-set-archive)
  and WPN marketing materials. Older seasons link PDFs, while newer lists can be
  inline. Read the complete slot descriptions, finish paragraphs and curated lists.
- Identify the physical pack's season, not merely the card's set symbol. Older
  printings can first appear in later curated pools. Some releases reuse another
  season's packs; require evidence before creating a new seasonal product.
- Extract PDFs with layout preserved, then inspect page breaks, wrapped names,
  bullet-only lines, ligature failures and list headings. Split shared, regular-only
  and foil-only sections before resolving names. Do not assume every list has 121
  names or fill a short list from a neighboring season.
- Capture each slot's rarity, DFC/Lesson exclusions, curated-card exclusions,
  replacement rules and accessory cards. Do not assume slots are disjoint, or that
  a set's mythics are eligible in the first slot: follow that season's wording.

## Resolve exact printings

Resolve names against the current `promo:promopack` catalog, retaining set code,
collector number and supported finish. Use physical front identity for split,
Adventure and Room cards; counting faces separately inflates pool and pack counts.
Explicit supplemental slots, such as M20's Japanese planeswalkers, need their own
queries rather than forcing them into the `promopack` classification.

When multiple stamped versions share a name, compare the PDF's surrounding set
groups, printing dates and catalogs or opening evidence. A set-level release date
alone cannot date a later stamped reprint. Record the reason for the chosen exact
printing; do not silently select the newest match or union every printing.

Treat typos, omitted cards and contradictory finish prose as evidence questions.
Normalize unmistakable spelling/extraction errors, but corroborate additions absent
from the list. Label catalog-backed corrections separately from official membership
and disclose inferences. DMU/BRO/ONE's single-list foil interpretation in the ledger
is a historical decision, not a rule for future ambiguous sources. Never flatten an
explicitly different foil list, such as SNC's, into a shared pool.

## Implement both layers

In **magic-search-engine**:

- Create `data/boosters/<set>-promo.yaml` and `<set>-promo-foil.yaml`, using distinct
  seasonal, curated and dark-frame sheets (and additional slots only if documented).
- Keep each booster's curated `rawquery` selectors in that booster YAML, grouped
  by set and collector number with expected counts. Do not move seasonal pools
  into `common.yaml`; that file is for generic reusable sheet behavior. Repeat
  identical membership locally in regular/foil files where justified, and preserve
  finish-specific differences. Put `foil` on the local sheet so it propagates
  through nested definitions.
- Use explicit filters for the seasonal slot and exclude known later special
  printings where needed. Broad `e:p<set>` queries can leak later distributions.
- Keep card eligibility separate from weights. Label estimated equal per-card
  weights and the repository's 2:1 rare/mythic convention as estimates. Preserve
  published replacement rates; group-selection probabilities must not accidentally
  overweight smaller set groups. Do not treat an observed sample as an exact drop rate.

In **mtg-sealed-content**:

- Use `scripts/sealed_yaml.py` to edit `data/products/SET.yaml`; contents are nested
  in product definitions, not separate `data/contents` files.
- Add or update regular and foil `BOOSTER_PACK` / `PROMOTIONAL` products, preserving
  verified identifiers. Reference the season's `promo` or `promo-foil` pack code and
  lowercase set code. Do not duplicate randomized card lists as decks or direct cards.
- Count gameplay cards only: M20 has four; the documented later seasons have three.
  Recheck new seasons rather than assuming this forever. Add Arena codes under
  `other: [{name: ...}]` only when the source lists them. Do not invent provider IDs.
- Update the research ledger with sources, slot decisions, exact-printing exceptions,
  uncertainties and the scope/date of coverage measurements.

## Validate membership, finishes and coverage

Freshly preprocess changed YAML with `PreprocessBooster` / `BoosterIndexer` and
compile it with `PackFactory` against the current `CardDatabase`. Testing only a
cached booster index can silently test the old definition.

Check every possible candidate's supported finish and resolve every candidate
through the production MTGJSON card UUID exporter. Sample openings for physical
card count and finish, but use full sheet membership—not samples—for coverage.
Check meaningful season-specific constraints: excluded Lessons/DFCs, foil-only
cards, replacement branches and exact-printing corrections.

For a full audit, form the expected set of `(set code, physical front collector
number, finish)` tuples for **every** current `promo:promopack` printing and supported
finish. Compare with the union of compiled products' candidate tuples. Report the
actual remaining tuples, not just names or a capped productless-page total. Also
verify every counted booster has a matching sealed product reference. Investigate
residuals individually; never add an orphan/catch-all sheet to manufacture coverage.
Recompute totals after changes; the ledger's past zero is not a permanent guarantee.

Run sealed structural validation and relevant tests; see the general audit's
[validation reference](../mtg-sealed-product-audit/references/validation.md).
Check pack codes, set references, counts and accessories against the companion
booster definitions. Review validator-generated `status.txt` or output changes
before staging; do not include unrelated generated files.

## Deliver

Follow the user's requested PR grouping and commit organization. Link companion
PRs and state that MSE booster definitions must be published before downstream
MTGJSON builds can resolve the sealed references. Report local checks separately
from remote CI and published downstream coverage. Summarize unmapped printings,
finish gaps and source limitations explicitly: zero coverage gaps does not prove
exact probabilities or every possible repeat appearance in later seasons.

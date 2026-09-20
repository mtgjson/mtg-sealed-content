---
name: mtg-secret-lair-bonus-audit
description: Audit Secret Lair bonus-card membership, finishes and estimated collation across mtg-sealed-content and magic-search-engine. Use for per-drop booster modeling, stained-glass/land/Sliver bonus cleanup, and unresolved bonus research.
---

# Secret Lair bonus audit

Model which bonus printings can actually occur in each drop. Keep random collation in search-engine boosters and sealed contents compact. Use the general [sealed-product audit](../mtg-sealed-product-audit/SKILL.md) for broader product/deck changes; this skill specializes in bonus slots.

## Scope and investigation

- Work in isolated worktrees. Fetch every touched repo and use fresh default-branch tips before measuring; never switch or overwrite the user's checkout. Follow local default-branch sync rules. Base each PR on its own repo's default branch.
- Audit the complete requested batch before editing products. Two-year batches are useful when requested, not a mandatory scope. Inventory finish/language variants, inherited `copy` entries, fixed bonuses, random pools, unknowns and exclusions. Include preorder-year releases shipped the following year (e.g. Secretversary 2020); distinguish those dates in the ledger. Bundles inherit constituent contents and are not extra independent drops.
- Build a product-to-printing evidence ledger with exact collector numbers, finishes, source links, confidence, and decisions. Separate membership evidence from odds. Reuse prior findings, but verify current upstream/PR state before treating them as implemented.
- Use official disclosures when available, then contemporary box-specific opening reports/videos, MTG Wiki and Magic Librarities checklists. Search Reddit, including `r/magicTCG`, `r/mtgfinance`, and `r/secretlair_collectors` (not `sld_collectors`). Read linked reports and comments; search snippets alone do not establish a complete pool.
- Search in both directions: drop names to bonus outcomes, and card names to originating drops. Include collector numbers and spelling variants, especially shortened names and different repeated-letter counts in stylized drop names (e.g. Vroom/Vroooom). Reddit’s own comment search and YouTube’s own search can expose reports that web search misses; use `mtg.wiki` rather than the old Fandom site.
- Treat auto-transcripts as navigation aids, not definitive card identification: they can substitute a plausible but wrong card name. Verify ambiguous or unexpected names against the video frame, as well as unnamed reveals such as “the bonus card” or “a Human.” Follow the opening from identifiable advertised cards to the bonus reveal, especially immediately after the final main card. Record timestamps, visible finish, product edition and whether identification is visual or transcript-based. Trace summary videos back to their sources and deduplicate reports by author, photo and opening. A brief megathread remark and a detailed photo post from the same person may describe one pull, not independent corroboration.
- Do a second investigation of problematic findings before deferring them. Prioritize contradictions, exact-number/finish ambiguity, missing rare replacements and drops with useful leads. Distinguish firsthand pulls from speculation, preview samples, reporting bias and reports that do not identify the box.

## Evidence decisions

A checklist is fallible. Multiple sites may repeat one table error rather than independently corroborate it. Preserve well-supported existing membership; do not mark a whole slot unknown just because one disputed card appears in a secondary source. Resolve a localized discrepancy using stronger opening evidence and an established drop-specific rule, then document the override. Color/theme alone is not a universal collation rule.

For a genuinely unsupported pool, use the existing sealed convention:

```yaml
other:
- name: Bonus card unknown
```

Distinguish an unresolved bonus from a confirmed absence. For a drop documented to contain no bonus card, use:

```yaml
other:
- name: Drop has no bonus card slot
```

An absent `card`/`pack`/`variable` field is not evidence that a physical bonus exists or that it does not. Check the product-specific evidence before introducing either annotation. Do not automatically add `Bonus card unknown` to every definition lacking a bonus mapping; never replace a confirmed absence with an unknown slot. Record the source supporting a no-bonus determination in the audit ledger.

Do not substitute a date-wide, color-wide, rarity-wide or catalog-wide fallback to make every card mapped. Preserve research leads outside executable contents. A lone observed pull does not establish a fixed bonus or exhaustive pool. If the entire bonus slot is unresolved, remove its speculative regular/replacement branches together; retain unrelated accessories and contents. Missing odds alone need not make known membership unknown when estimated weights are authorized.

After investigating plausible alternatives, multiple supported drop-specific outcomes can form a documented working pool when estimated weights are authorized. An unverified candidate alone need not keep the drop unresolved: exclude it unless evidence supports inclusion. Distinguish this practical closure from a manufacturer-guaranteed exhaustive checklist, document remaining uncertainty, and revise the pool when new evidence emerges. This does not justify ignoring contradictory reports or treating a lone pull as a complete pool.

## Modeling

- `mtg-sealed-content/data/contents/SLD.yaml`: supported fixed bonuses stay direct `card` entries. Random bonus slots reference a complete drop-specific booster in `taw/magic-search-engine/data/boosters/sld-bonus-<drop>.yaml`. Do not expand sealed YAML into large lists of single-card alternatives.
- A pack reference must resolve to a real, compiled definition. Add missing boosters and fix incorrect ones in their owning repo. A regular pool plus possible Blueprint/Petitioner/Apostle replacements belongs inside the same complete bonus-slot booster, not as separate packs that accidentally add cards.
- Use explicit printing membership. Share a drop's booster across finish/language variants only when the bonus pool and finish agree; split when they differ. Preserve `copy` inheritance instead of adding conflicting content beside it.
- Do not remove a card from one drop because another drop also contains it. Do not infer insertion dates from database release dates or universal eligibility from a superdrop-wide checklist.
- Use documented estimates only when authorized. Equal weights and historical 5%/2% replacement conventions are assumptions, not official rates or defaults for new drops. Do not derive odds from market prices. Distinguish category probability from per-card probability and normalize to the correct number of physical bonus cards.
- Retire obsolete shared boosters only after checking all consumers, including out-of-batch products, copies and nested alternatives. If their removal affects other years, disclose the scope and resolve those references too. Do not leave dangling codes or silently assign new generic pools.

Read [references/evidence-and-validation.md](references/evidence-and-validation.md) for source pitfalls, schema examples and finish-propagation checks before implementation.

## Delivery

Maintain one decision ledger for the whole batch, including unchanged and unresolved drops. File remaining research **by year**, updating existing issues where appropriate; resolve issues when their question is settled. Do not file an empty issue for a cleared year.

Before calling a drop resolved, ensure its compiled booster, effective sealed references for all affected editions, cached card counts, master evidence ledger, year-issue status and PR title/body agree with the final implementation. Research agreement alone is not implemented closure. Update master documents and existing issue bodies in place rather than adding chronological follow-up notes or comments; keep a year issue open while other research items remain.

Use existing session authorization for PRs; this skill itself does not authorize publishing. Keep PRs independent and link companion changes. State the coordinated publication requirements for added/removed pack codes and downstream rebuilds. Post PR links as they open when requested, then give a final table with counts and material uncertainties. Keep independent fixed-finish/code changes in separate commits or PRs when requested. Do not conflate local validation with a published downstream result.

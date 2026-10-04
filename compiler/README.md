# mtg-sealed-choices

The recipe compiler used by mtg-sealed-content and MTGJSON. Requires Python 3.10+
and has no runtime dependencies. Install from this repository with
`pip install ./compiler` (or the repository's requirements.txt).

`ChoiceGroups(contents, factory, name=None)` expands `variable_mode` counts,
replacement and weights. The factory returns a caller-owned component with
`chance`, `weight` and `merge(other)`. Recursive components construct their own
ChoiceGroups. `merge()` retains independent groups; `serialize(callback)` emits
one `configs` array per group. Catalog lookup, language selection and logging stay in the callers.

The engine preserves the existing unordered-combinations semantics, including
multiplication of component chances. It does not reinterpret replacement as
ordered independent draws or expand the Cartesian product of nested choices.

Consumers pin an immutable source commit (with `#subdirectory=compiler`) until
a package-index release is available. The version lives in `pyproject.toml`;
bump it for behavior/API changes and run the contract tests before updating a
consumer's pin. Do not copy this module into consumers.

## Shared recipe model (0.2.0)

`mtg_sealed_choices.model` owns the Card, Pack, Deck, Sealed, Other and Product
objects: parsing, merging, serialization, recursive resolution traversal and
direct deck links. Consumers subclass leaf types for catalog lookups and Product
for diagnostics, product UUID resolution and unresolved-card filtering. Nested
choices instantiate the same adapter subclass so its policies apply at every
level. Public adapter names remain compatible with existing callers.

`mtg_sealed_choices.links` owns card/finish identity, explicit-card extraction,
deck-board enumeration, recursive variable membership and reverse-index output.
`variable_cards` unions reachable cards across every nested choice; it does not
calculate probabilities. Consumer callbacks supply catalog and language context.

The sealed repository still owns YAML editing, placeholders/orphans, downloading
AllPrintings and status.txt. MTGJSON still owns pipeline inputs, language-aware
UUIDs, unresolved-card filtering and published model validation. Booster finish
lookup also remains local: the sealed adapter has legacy H1R/MH2/STA etched
fallbacks absent from the pipeline adapter. These policies were not silently
unified during extraction.

Tests cover nested resolution hooks, weighted choices, metadata, card membership,
direct deck links and deterministic reverse-index output. Both consumers use
these implementations rather than maintaining another copy.

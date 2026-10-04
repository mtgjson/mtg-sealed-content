# mtg-sealed-choices

The choice engine used by mtg-sealed-content and MTGJSON. Requires Python 3.10+
and has no runtime dependencies. Install from this repository with
`pip install ./compiler` (or the repository's requirements.txt).

`ChoiceGroups(contents, factory, name=None)` expands `variable_mode` counts,
replacement and weights. The factory returns a caller-owned component with
`chance`, `weight` and `merge(other)`. Recursive components construct their own
ChoiceGroups. `merge()` retains independent groups; `serialize(callback)` emits
one `configs` array per group. UUID lookup, card/deck handling, language selection
and logging stay in the callers.

Version 0.1.0 preserves the existing unordered-combinations semantics, including
multiplication of component chances. It does not reinterpret replacement as
ordered independent draws or expand the Cartesian product of nested choices.

Consumers pin an immutable source commit (with `#subdirectory=compiler`) until
a package-index release is available. The version lives in `pyproject.toml`;
bump it for behavior/API changes and run the contract tests before updating a
consumer's pin. Do not copy this module into consumers.

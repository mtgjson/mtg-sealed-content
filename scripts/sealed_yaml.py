"""Read and write the per-set sealed product YAML.

Each set lives in data/products/SET.yaml, with each product's contents nested under
a `contents:` key. Contents used to live in separate data/contents/SET.yaml files,
until #782 folded them in.

Scripts work on the in-memory form, {"code": ..., "products": {name: entry}} where
an entry may carry a "contents" mapping, and save through save_set(). That is the
only way scripts write these files, and it refuses a save that would drop a product
or drop or overwrite existing contents, unless the caller allows that specific
field for that specific product. A script that rewrites a product entry can
therefore no longer wipe researched contents.
"""
if __package__:
    from .atomic_write import atomic_write
else:
    from atomic_write import atomic_write

from pathlib import Path

import yaml

LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# Product-level keys in file order: what the product is, where to buy it, then what
# is inside it. Anything else is rejected by the validator.
KEY_ORDER = ("category", "subtype", "release_date", "language", "identifiers", "contents")
PRODUCT_KEYS = frozenset(KEY_ORDER)
# Keys that belong inside a product's contents, so the validator can tell a
# contributor where a misplaced one should go.
CONTENT_KEYS = frozenset({
    "card", "pack", "deck", "sealed", "other", "variable", "variable_mode",
    "card_count", "copy", "chance", "weight",
})


class WriterRuleError(ValueError):
    """A save would drop a product, or drop or overwrite existing contents."""


def products_dir(root="."):
    return Path(root) / "data" / "products"


def set_stems(root="."):
    """File stems of every set, e.g. "ONE" or "CON_", in a stable order."""
    return sorted(path.stem for path in products_dir(root).glob("*.yaml"))


def set_exists(stem, root="."):
    return (products_dir(root) / f"{stem}.yaml").exists()


def new_set(code):
    return {"code": code.lower(), "products": {}}


def _read(path):
    with open(path, "rb") as stream:
        return yaml.load(stream, Loader=LOADER) or {}


def load_set(stem, root="."):
    data = _read(products_dir(root) / f"{stem}.yaml")
    return {
        "code": data["code"],
        "products": {name: dict(entry or {}) for name, entry in (data.get("products") or {}).items()},
    }


def iter_sets(root="."):
    for stem in set_stems(root):
        yield stem, load_set(stem, root)


def check_writer_rule(old, new, allow):
    """Raise WriterRuleError if saving `new` over `old` loses products or contents.

    Adding products, fields and contents is always fine. Removing a product is
    never allowed from a script. Removing or changing an existing contents field
    is allowed only when `allow` names that field for that product.
    """
    problems = []
    for name, old_entry in old["products"].items():
        if name not in new["products"]:
            problems.append(f"would drop product {name!r}")
            continue
        old_contents = old_entry.get("contents") or {}
        new_contents = new["products"][name].get("contents") or {}
        allowed = allow.get(name, ())
        if not isinstance(old_contents, dict) or not isinstance(new_contents, dict):
            # Malformed contents (the validator rejects them) can only be kept as-is
            if new_contents != old_contents:
                problems.append(f"would replace the contents of {name!r}")
            continue
        for field, value in old_contents.items():
            if field in allowed:
                continue
            if field not in new_contents:
                problems.append(f"would remove {field!r} from the contents of {name!r}")
            elif new_contents[field] != value:
                problems.append(f"would overwrite {field!r} in the contents of {name!r}")
    if problems:
        raise WriterRuleError(f"refusing to save set {old['code']}: " + "; ".join(problems))


def save_set(stem, data, allow=None, root="."):
    """Write one set, after checking the writer rule.

    `allow` maps a product name to the contents fields this save may overwrite or
    remove for that product, e.g. {"Some Product": {"card_count"}}. There is
    deliberately no way to replace a whole entry or a whole contents block.
    """
    if set_exists(stem, root):
        check_writer_rule(load_set(stem, root), data, allow or {})
    with atomic_write(products_dir(root) / f"{stem}.yaml") as stream:
        stream.write(render_set(data))


def _sorted(value):
    if isinstance(value, dict):
        return {key: _sorted(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sorted(item) for item in value]
    return value


def _ordered(entry):
    entry = {key: value for key, value in entry.items() if key != "contents" or value}
    keys = [key for key in KEY_ORDER if key in entry] + sorted(set(entry) - PRODUCT_KEYS)
    return {key: _sorted(entry[key]) for key in keys}


def render_set(data):
    """The products file text for one set."""
    document = {
        "code": data["code"],
        "products": {name: _ordered(entry) for name, entry in sorted(data["products"].items())},
    }
    return yaml.dump(document, Dumper=yaml.SafeDumper, allow_unicode=True, sort_keys=False)


def layout_errors(root="."):
    """A data/contents/ file that came back, usually from a branch older than #782.

    Nothing here reads data/contents/ any more, so whatever it holds would be
    silently lost. Worse, an MTGJSON reader that still has the old-layout fallback
    treats the whole tree as the old layout when that directory exists, which
    would empty the contents of every other set.
    """
    leftovers = sorted(path.name for path in (Path(root) / "data" / "contents").glob("*.yaml"))
    if not leftovers:
        return []
    return [
        f"data/contents/ is no longer read, but it has {', '.join(leftovers)}. "
        f"Move each product's entry under its `contents:` key in data/products/ "
        f"and delete the file."
    ]

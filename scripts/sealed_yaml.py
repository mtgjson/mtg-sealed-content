"""Read and write the per-set sealed product YAML in either on-disk layout.

Split layout (today): data/products/SET.yaml holds each product's definition and
data/contents/SET.yaml what is inside it. Merged layout (after the planned
migration): only data/products/SET.yaml, with each product's contents nested under
a `contents:` key. The layout is decided once for the whole tree: merged when
data/contents/ is absent, split otherwise.

Scripts work on the merged form in memory, {"code": ..., "products": {name: entry}}
where an entry may carry a "contents" mapping, and save through save_set(). That is
the only way scripts write these files, and it refuses a save that would drop a
product or drop or overwrite existing contents, unless the caller allows that
specific field for that specific product. A script that rewrites a product entry
can therefore no longer wipe researched contents.
"""
if __package__:
    from .atomic_write import atomic_write
else:
    from atomic_write import atomic_write

from pathlib import Path

import yaml

LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)

# Product-level keys in merged-layout order: what the product is, where to buy it,
# then what is inside it. Anything else is rejected by the validator.
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


def contents_dir(root="."):
    return Path(root) / "data" / "contents"


def is_split(root="."):
    return contents_dir(root).is_dir()


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
    """Load one set in the merged in-memory form, whatever the layout on disk.

    In the split layout, empty contents placeholders ({}, [] or null) and contents
    entries without a product are kept aside under "_placeholders" and "_orphans",
    so saving the set writes them back unchanged.
    """
    data = _read(products_dir(root) / f"{stem}.yaml")
    result = {
        "code": data["code"],
        "products": {name: dict(entry or {}) for name, entry in (data.get("products") or {}).items()},
    }
    if is_split(root):
        path = contents_dir(root) / f"{stem}.yaml"
        described = (_read(path).get("products") or {}) if path.exists() else {}
        placeholders, orphans = {}, {}
        for name, value in described.items():
            if name not in result["products"]:
                orphans[name] = value
            elif value:
                result["products"][name]["contents"] = value
            else:
                placeholders[name] = value
        result["_placeholders"] = placeholders
        result["_orphans"] = orphans
    return result


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
    new_orphans = new.get("_orphans") or {}
    for name, value in (old.get("_orphans") or {}).items():
        if value and new_orphans.get(name) != value:
            problems.append(f"would drop the contents entry {name!r}, which has no product")
    if problems:
        raise WriterRuleError(f"refusing to save set {old['code']}: " + "; ".join(problems))


def save_set(stem, data, allow=None, root="."):
    """Write one set in the current layout, after checking the writer rule.

    `allow` maps a product name to the contents fields this save may overwrite or
    remove for that product, e.g. {"Some Product": {"card_count"}}. There is
    deliberately no way to replace a whole entry or a whole contents block.
    """
    if set_exists(stem, root):
        check_writer_rule(load_set(stem, root), data, allow or {})
    if is_split(root):
        definitions, described = render_split(data)
        with atomic_write(products_dir(root) / f"{stem}.yaml") as stream:
            stream.write(definitions)
        with atomic_write(contents_dir(root) / f"{stem}.yaml") as stream:
            stream.write(described)
    else:
        with atomic_write(products_dir(root) / f"{stem}.yaml") as stream:
            stream.write(render_merged(data))


def render_split(data):
    """The (products file, contents file) text for one set in the split layout.

    Both are plain yaml.safe_dump output, byte for byte what the scripts have
    always written. Products without contents get their original placeholder back
    (or {}), and empty contents entries without a product are dropped, as the old
    sync pass in load_new_products.py did.
    """
    placeholders = data.get("_placeholders") or {}
    definitions, described = {}, {}
    for name, entry in data["products"].items():
        definitions[name] = {key: value for key, value in entry.items() if key != "contents"}
        described[name] = entry.get("contents") or placeholders.get(name, {})
    for name, value in (data.get("_orphans") or {}).items():
        if value:
            described[name] = value
    return (
        yaml.safe_dump({"code": data["code"], "products": definitions}, allow_unicode=True),
        yaml.safe_dump({"code": data["code"], "products": described}, allow_unicode=True),
    )


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


def render_merged(data):
    """The products file text for one set in the merged layout."""
    document = {
        "code": data["code"],
        "products": {name: _ordered(entry) for name, entry in sorted(data["products"].items())},
    }
    return yaml.dump(document, Dumper=yaml.SafeDumper, allow_unicode=True, sort_keys=False)


def layout_errors(root="."):
    """Problems with the on-disk layout that the loaders would otherwise paper over.

    In the split layout every contents entry must belong to a product: a contents
    entry without one is how a one-sided rename silently loses data. A product
    without a contents entry loses nothing, and the next save gives it an empty
    placeholder, so that is allowed. Nested contents while data/contents/ exists
    usually means a stale data/contents/ file came back after the conversion, so
    that gets one message pointing at `convert_layout.py fold`. The merged layout
    has nothing to reconcile.
    """
    if not is_split(root):
        return []
    errors = []
    stems = set(set_stems(root))
    leftovers = sorted(path.stem for path in contents_dir(root).glob("*.yaml"))
    nested = []
    for stem in sorted(set(leftovers) - stems):
        errors.append(f"data/contents/{stem}.yaml has no data/products/{stem}.yaml")
    for stem in sorted(stems):
        definitions = _read(products_dir(root) / f"{stem}.yaml")
        defined = definitions.get("products") or {}
        nested += [
            (stem, name) for name, entry in defined.items()
            if isinstance(entry, dict) and "contents" in entry
        ]
        path = contents_dir(root) / f"{stem}.yaml"
        if not path.exists():
            continue
        described = _read(path)
        if definitions.get("code") != described.get("code"):
            errors.append(
                f"{stem}: code {definitions.get('code')!r} in data/products "
                f"but {described.get('code')!r} in data/contents"
            )
        for name in sorted(set(described.get("products") or {}) - set(defined)):
            errors.append(f"{stem}: contents entry {name!r} has no product in data/products/{stem}.yaml")
    nested_sets = sorted({stem for stem, _ in nested})
    if len(nested_sets) > len(leftovers):
        # Most of the tree is merged: one message instead of one per product
        errors.insert(0, (
            f"data/contents/ still exists, but {len(nested_sets)} sets in data/products/ "
            f"nest their contents. If data/ is in the merged layout, fold the leftover files "
            f"with `python scripts/convert_layout.py fold {' '.join(leftovers)}`"
        ))
    else:
        for stem, name in nested:
            errors.append(f"{stem}: product {name!r} nests contents while data/contents/ still exists")
    return errors

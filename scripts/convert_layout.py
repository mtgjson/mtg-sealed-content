"""Convert data/ between the split and merged sealed product layouts.

    python scripts/convert_layout.py check          # round-trip every set in memory, write nothing
    python scripts/convert_layout.py merge          # split -> merged: nest contents, delete data/contents/
    python scripts/convert_layout.py split          # merged -> split: the rollback
    python scripts/convert_layout.py fold SET ...   # fold leftover data/contents/SET.yaml files into a merged tree

The converted files are generated, never edited by hand: run `merge` on the exact
main commit the conversion lands on rather than rebasing an old conversion.

`fold` is for pull requests opened before the conversion. First merge the last
pre-conversion commit of main into the branch, so its data/contents/SET.yaml
includes everything main had, then merge the conversion commit, keep the branch's
version of data/contents/SET.yaml, and fold it. Skipping the first step would let a
stale branch undo changes made on main. Folding deliberately replaces that set's
contents with the branch's version, so it does not go through the writer rule.
"""
if __package__:
    from .atomic_write import atomic_write
    from . import sealed_yaml
else:
    from atomic_write import atomic_write
    import sealed_yaml

import argparse
import sys

import yaml


def _comparable(data):
    """A set without the split-layout bookkeeping, for comparing across layouts."""
    return {
        "code": data["code"],
        "products": {
            name: {key: value for key, value in entry.items() if key != "contents" or value}
            for name, entry in data["products"].items()
        },
    }


def _parse(text):
    return yaml.load(text, Loader=sealed_yaml.LOADER) or {}


def _round_trip(data, split):
    """Render one set in the other layout and read it back."""
    if split:
        rendered = _parse(sealed_yaml.render_merged(data))
        return _comparable(rendered)
    definitions, described = (_parse(text) for text in sealed_yaml.render_split(data))
    back = {"code": definitions["code"], "products": {
        name: dict(entry) for name, entry in definitions["products"].items()}}
    for name, value in described["products"].items():
        if value:
            back["products"][name]["contents"] = value
    return back


def _refuse_layout_errors():
    errors = sealed_yaml.layout_errors()
    for error in errors:
        print(error)
    if errors:
        raise SystemExit("Fix the layout errors above first")


def check():
    split = sealed_yaml.is_split()
    _refuse_layout_errors()
    sets = products = described = 0
    failed = []
    for stem, data in sealed_yaml.iter_sets():
        sets += 1
        products += len(data["products"])
        described += sum(1 for entry in data["products"].values() if entry.get("contents"))
        if _round_trip(data, split) != _comparable(data):
            failed.append(stem)
    if failed:
        raise SystemExit(f"Round trip changed these sets: {', '.join(failed)}")
    layout = "split" if split else "merged"
    print(f"{sets} sets, {products} products ({described} with contents) "
          f"round-trip cleanly from the {layout} layout")


def merge():
    if not sealed_yaml.is_split():
        raise SystemExit("data/ is already in the merged layout")
    _refuse_layout_errors()
    sets = list(sealed_yaml.iter_sets())
    for stem, data in sets:
        with atomic_write(sealed_yaml.products_dir() / f"{stem}.yaml") as stream:
            stream.write(sealed_yaml.render_merged(data))
    for path in sealed_yaml.contents_dir().glob("*.yaml"):
        path.unlink()
    sealed_yaml.contents_dir().rmdir()
    for stem, data in sets:
        if _comparable(sealed_yaml.load_set(stem)) != _comparable(data):
            raise SystemExit(f"{stem} did not survive the conversion")
    print(f"Merged {len(sets)} sets; data/contents/ removed")


def split():
    if sealed_yaml.is_split():
        raise SystemExit("data/ is already in the split layout")
    sets = list(sealed_yaml.iter_sets())
    sealed_yaml.contents_dir().mkdir()
    for stem, data in sets:
        definitions, described = sealed_yaml.render_split(data)
        with atomic_write(sealed_yaml.products_dir() / f"{stem}.yaml") as stream:
            stream.write(definitions)
        with atomic_write(sealed_yaml.contents_dir() / f"{stem}.yaml") as stream:
            stream.write(described)
    for stem, data in sets:
        if _comparable(sealed_yaml.load_set(stem)) != _comparable(data):
            raise SystemExit(f"{stem} did not survive the conversion")
    print(f"Split {len(sets)} sets into data/products/ and data/contents/")


def fold(stems):
    leftovers = sorted(path.stem for path in sealed_yaml.contents_dir().glob("*.yaml"))
    if len(leftovers) >= len(sealed_yaml.set_stems()):
        raise SystemExit("data/ is in the split layout; use `merge` instead")
    for stem in stems:
        path = sealed_yaml.contents_dir() / f"{stem}.yaml"
        if stem not in leftovers:
            raise SystemExit(f"{path} does not exist")
        with open(sealed_yaml.products_dir() / f"{stem}.yaml", "rb") as stream:
            merged = yaml.load(stream, Loader=sealed_yaml.LOADER)
        with open(path, "rb") as stream:
            described = (yaml.load(stream, Loader=sealed_yaml.LOADER) or {}).get("products") or {}
        products = merged["products"]
        orphans = sorted(set(described) - set(products))
        if orphans:
            raise SystemExit(f"{path} describes products that don't exist: {', '.join(orphans)}")
        for name, value in described.items():
            if value:
                products[name]["contents"] = value
            else:
                products[name].pop("contents", None)
        with atomic_write(sealed_yaml.products_dir() / f"{stem}.yaml") as stream:
            stream.write(sealed_yaml.render_merged(merged))
        path.unlink()
        print(f"Folded {path} into data/products/{stem}.yaml")
    if not any(sealed_yaml.contents_dir().iterdir()):
        sealed_yaml.contents_dir().rmdir()


def parse_args(argv=None):
    parser = argparse.ArgumentParser("convert_layout", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="round-trip every set in memory, write nothing")
    commands.add_parser("merge", help="split -> merged")
    commands.add_parser("split", help="merged -> split (rollback)")
    fold_parser = commands.add_parser("fold", help="fold leftover data/contents/SET.yaml files")
    fold_parser.add_argument("sets", nargs="+", metavar="SET")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.command == "check":
        check()
    elif args.command == "merge":
        merge()
    elif args.command == "split":
        split()
    else:
        fold(args.sets)


if __name__ == "__main__":
    main(sys.argv[1:])

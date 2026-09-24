"""Generate and publish CI content without rewriting another writer's commits."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


MESSAGES = {
    "daily": "Pull new daily content",
    "caches": "Build cached content",
    "weekly": "Pull new weekly content",
}


def git(*args, check=True):
    return subprocess.run(
        ["git", *args], text=True, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, check=check,
    )


def revision(ref):
    return git("rev-parse", ref).stdout.strip()


def run_step(label, *args):
    print(f"::group::{label}", flush=True)
    try:
        # Do not print arguments: the product loader accepts a credential.
        result = subprocess.run([sys.executable, *args])
        if result.returncode:
            raise RuntimeError(f"{label} failed ({result.returncode})")
    finally:
        print("::endgroup::", flush=True)


def validate_output(filename, minimum):
    with open(filename) as source:
        count = len(json.load(source))
    if count < minimum:
        raise RuntimeError(f"{filename} has {count} entries; expected >= {minimum}")
    print(f"{filename} has {count} entries", flush=True)


def rebuild(mode):
    if mode == "weekly":
        run_step("Build Gatherer mapping", "scripts/gatherer_original_printing_details_generator.py")
        validate_output("outputs/gatherer_mapping.json", 50000)
        return
    if mode == "daily":
        run_step("Import decks", "scripts/import_new_decks.py")
        run_step("Load products", "scripts/load_new_products.py", os.environ["TCG_AUTH"])
        run_step("Associate names", "scripts/check_product_fuzzy.py", "--auto", "--auto-margin", "3")
    run_step("Rebuild status and deck map", "scripts/contents_validator.py", "--status")
    run_step("Compile products", "scripts/new_products_compiler.py")
    run_step("Map cards", "scripts/card_to_product_compiler.py", "-o", "outputs/card_map.json")
    if mode == "daily":
        run_step("Map tokens", "-m", "scripts.tokens.main")
    validate_output("outputs/card_map.json", 1)


def commit_outputs(mode, base):
    paths = [":(glob)outputs/*.json"] if mode == "weekly" else ["data", "outputs", "status.txt"]
    git("add", "--all", "--", *paths)
    diff = git("diff", "--cached", "--quiet", check=False)
    if diff.returncode == 0:
        return False
    if diff.returncode != 1:
        diff.check_returncode()
    git(
        "-c", "user.name=github-actions[bot]",
        "-c", "user.email=41898282+github-actions[bot]@users.noreply.github.com",
        "commit", "-m", MESSAGES[mode], "-m", f"Generated-from: {base}",
    )
    return True


def require_clean():
    if git("status", "--porcelain").stdout.strip():
        raise RuntimeError("Unexpected changes outside the generated paths; refusing to publish")


def rejected_for_advance(result):
    # Remote hook/protection/authentication failures must not become fallback PRs.
    for line in result.stdout.splitlines():
        fields = line.split("\t")
        if (len(fields) == 3 and fields[0] == "!"
                and fields[1] == "HEAD:refs/heads/main"
                and fields[2] in {"[rejected] (fetch first)", "[rejected] (non-fast-forward)"}):
            return True
    return False


def fetch_main():
    git("fetch", "origin", "refs/heads/main:refs/remotes/origin/main")
    return revision("origin/main")


def check_freshness():
    base = git("show", "-s", "--format=%(trailers:key=Generated-from,valueonly)", "HEAD").stdout.strip()
    if base != fetch_main():
        raise RuntimeError("Generated content is stale: rerun its publishing workflow against current main")


def open_pr(branch, mode, base):
    repository = os.environ["GITHUB_REPOSITORY"]
    run_url = f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{repository}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    body = (
        f"The normal push was rejected because `main` advanced during generation. "
        f"This run regenerated the {mode} content from `{base}` before opening this draft.\n\n"
        "Review the generated changes and run the PR checks before marking it ready. "
        "If main advances again, rerun the publishing workflow and close this superseded draft; "
        "rebasing generated files alone does not rebuild their contents.\n\n"
        f"Workflow run: {run_url}\n"
    )
    with tempfile.TemporaryDirectory() as directory:
        body_file = Path(directory) / "body.md"
        body_file.write_text(body)
        subprocess.run([
            "gh", "pr", "create", "--repo", repository, "--base", "main",
            "--head", branch, "--draft", "--title", MESSAGES[mode],
            "--body-file", str(body_file),
        ], check=True)


def publish(mode, generate=None, create_pr=None):
    generate = generate or (lambda: rebuild(mode))
    create_pr = create_pr or open_pr
    require_clean()
    base = revision("HEAD")
    if base != revision("origin/main"):
        raise RuntimeError("Publishing must start from the checked-out origin/main revision")
    generate()
    changed = commit_outputs(mode, base)
    require_clean()
    if not changed:
        print("No generated changes to publish")
        return
    push = git("push", "--porcelain", "origin", "HEAD:refs/heads/main", check=False)
    print(push.stdout, end="", flush=True)
    print(push.stderr, end="", file=sys.stderr, flush=True)
    if push.returncode == 0:
        return
    if not rejected_for_advance(push):
        push.check_returncode()
    latest = fetch_main()
    if latest == base or git("merge-base", "--is-ancestor", base, latest, check=False).returncode:
        raise RuntimeError("main did not simply advance; refusing automatic recovery")

    # Discard only this run's committed output, then rebuild from the new source.
    # Never merge/rebase stale generated files onto edits made during the run.
    git("checkout", "--detach", latest)
    generate()
    changed = commit_outputs(mode, latest)
    require_clean()
    if not changed:
        print("Current main already contains the generated content")
        return
    branch = f"codex/generated/{mode}-{os.environ['GITHUB_RUN_ID']}-{os.environ['GITHUB_RUN_ATTEMPT']}"
    git("push", "origin", f"HEAD:refs/heads/{branch}")
    create_pr(branch, mode, latest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=MESSAGES, nargs="?")
    parser.add_argument("--check-freshness", action="store_true")
    args = parser.parse_args()
    if args.check_freshness:
        check_freshness()
    elif args.mode:
        publish(args.mode)
    else:
        parser.error("mode is required when publishing")


if __name__ == "__main__":
    main()

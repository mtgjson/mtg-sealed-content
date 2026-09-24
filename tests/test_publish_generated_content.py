import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts import publish_generated_content as publisher


class PublishingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        # Isolate hooks, signing and identity from the developer's Git settings.
        self.environment = patch.dict(os.environ, {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.invalid",
            "GITHUB_RUN_ID": "123", "GITHUB_RUN_ATTEMPT": "2",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.remote = self.root / "remote.git"
        self.worker = self.root / "worker"
        self.editor = self.root / "editor"
        self.git(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.root, "clone", str(self.remote), str(self.worker))
        for name in ("data", "outputs"):
            (self.worker / name).mkdir()
        (self.worker / "data/source").write_text("original")
        (self.worker / "outputs/result.json").write_text('"original"')
        (self.worker / "status.txt").write_text("status")
        self.git(self.worker, "add", ".")
        self.git(self.worker, "commit", "-m", "Initial")
        self.git(self.worker, "push", "origin", "main")
        self.git(self.root, "clone", str(self.remote), str(self.editor))
        previous = Path.cwd()
        os.chdir(self.worker)
        self.addCleanup(os.chdir, previous)
        self.create_pr = Mock()

    def git(self, cwd, *args):
        return subprocess.run(
            ["git", *args], cwd=cwd, check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()

    def generate(self):
        source = Path("data/source").read_text()
        Path("outputs/result.json").write_text(f'"generated from {source}"')

    def advance_main(self, output=None):
        (self.editor / "data/source").write_text("human edit")
        if output is not None:
            (self.editor / "outputs/result.json").write_text(output)
        self.git(self.editor, "add", ".")
        self.git(self.editor, "commit", "-m", "Concurrent human edit")
        self.git(self.editor, "push", "origin", "main")
        return self.git(self.editor, "rev-parse", "HEAD")

    def publish(self, generate=None, mode="caches"):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            publisher.publish(mode, generate or self.generate, self.create_pr)

    def test_normal_push_is_fast_forward(self):
        old = self.git(self.remote, "rev-parse", "main")
        self.publish()
        self.assertEqual(self.git(self.remote, "rev-parse", "main^"), old)
        self.assertEqual(self.git(self.remote, "show", "main:outputs/result.json"), '"generated from original"')
        self.create_pr.assert_not_called()

    def test_feature_branch_commits_cannot_be_published_to_main(self):
        Path("data/source").write_text("feature edit")
        self.git(self.worker, "commit", "-am", "Unrelated feature")
        with self.assertRaisesRegex(RuntimeError, "origin/main revision"):
            self.publish()
        self.assertEqual(self.git(self.remote, "show", "main:data/source"), "original")
        self.create_pr.assert_not_called()

    def test_pr_creation_failure_keeps_recovery_branch_and_fails(self):
        calls = []

        def generate():
            self.generate()
            calls.append(1)
            if len(calls) == 1:
                self.advance_main()

        self.create_pr.side_effect = RuntimeError("PR creation forbidden")
        with self.assertRaisesRegex(RuntimeError, "PR creation forbidden"):
            self.publish(generate)
        self.assertEqual(
            self.git(self.remote, "show", "codex/generated/caches-123-2:outputs/result.json"),
            '"generated from human edit"',
        )
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), self.git(self.editor, "rev-parse", "HEAD"))

    def test_no_changes_does_not_commit_or_open_pr(self):
        old = self.git(self.remote, "rev-parse", "main")
        self.publish(lambda: None)
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), old)
        self.create_pr.assert_not_called()

    def test_concurrent_edit_regenerates_and_opens_pr_without_changing_main(self):
        calls = []

        def generate():
            self.generate()
            calls.append(Path("data/source").read_text())
            if len(calls) == 1:
                self.advance_main()

        self.publish(generate)
        latest = self.git(self.editor, "rev-parse", "HEAD")
        branch = "codex/generated/caches-123-2"
        self.assertEqual(calls, ["original", "human edit"])
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), latest)
        self.assertEqual(self.git(self.remote, "rev-parse", branch + "^"), latest)
        self.assertEqual(self.git(self.remote, "show", branch + ":data/source"), "human edit")
        self.assertEqual(self.git(self.remote, "show", branch + ":outputs/result.json"), '"generated from human edit"')
        self.create_pr.assert_called_once_with(branch, "caches", latest)
        publisher.check_freshness()

    def test_upstream_already_has_regenerated_result_does_not_open_empty_pr(self):
        calls = []

        def generate():
            self.generate()
            calls.append(1)
            if len(calls) == 1:
                self.advance_main('"generated from human edit"')

        self.publish(generate)
        self.assertEqual(len(calls), 2)
        self.create_pr.assert_not_called()

    def test_hook_rejection_is_not_treated_as_a_race(self):
        hook = self.remote / "hooks/pre-receive"
        hook.write_text("#!/bin/sh\necho 'push forbidden' >&2\nexit 1\n")
        hook.chmod(0o755)
        old = self.git(self.remote, "rev-parse", "main")
        with self.assertRaises(subprocess.CalledProcessError):
            self.publish()
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), old)
        self.create_pr.assert_not_called()

    def test_unavailable_remote_does_not_open_pr(self):
        self.git(self.worker, "remote", "set-url", "origin", str(self.root / "missing.git"))
        with self.assertRaises(subprocess.CalledProcessError):
            self.publish()
        self.create_pr.assert_not_called()

    def test_failed_regeneration_does_not_publish_stale_branch(self):
        calls = []

        def generate():
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError("generator failed")
            self.generate()
            self.advance_main()

        with self.assertRaisesRegex(RuntimeError, "generator failed"):
            self.publish(generate)
        self.assertEqual(self.git(self.remote, "for-each-ref", "--format=%(refname)", "refs/heads"), "refs/heads/main")
        self.create_pr.assert_not_called()

    def test_unexpected_changes_are_not_published(self):
        old = self.git(self.remote, "rev-parse", "main")

        def generate():
            self.generate()
            Path("unrelated.txt").write_text("not generated content")

        with self.assertRaisesRegex(RuntimeError, "Unexpected changes"):
            self.publish(generate)
        self.assertEqual(self.git(self.remote, "rev-parse", "main"), old)
        self.create_pr.assert_not_called()

    def test_second_main_advance_and_rebase_cannot_hide_stale_output(self):
        old = self.git(self.worker, "rev-parse", "HEAD")
        self.generate()
        publisher.commit_outputs("caches", old)
        latest = self.advance_main()
        with self.assertRaisesRegex(RuntimeError, "stale"):
            publisher.check_freshness()
        self.git(self.worker, "rebase", "origin/main")
        self.assertEqual(self.git(self.worker, "rev-parse", "HEAD^"), latest)
        with self.assertRaisesRegex(RuntimeError, "stale"):
            publisher.check_freshness()

    def test_weekly_only_commits_top_level_output_json(self):
        self.publish(mode="weekly")
        self.assertEqual(self.git(self.remote, "diff-tree", "--no-commit-id", "--name-only", "-r", "main"), "outputs/result.json")

    def test_degraded_outputs_are_rejected(self):
        Path("outputs/result.json").write_text("{}")
        with self.assertRaisesRegex(RuntimeError, "expected >= 1"):
            publisher.validate_output("outputs/result.json", 1)
        Path("outputs/result.json").write_text('{"one": 1}')
        with self.assertRaisesRegex(RuntimeError, "expected >= 50000"):
            publisher.validate_output("outputs/result.json", 50000)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from nova_school_server.release_notes import build_release_history, render_changelog, render_release_notes


class ReleaseNotesTests(unittest.TestCase):
    def test_build_release_history_and_render_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            self._git(repo, "init")
            self._git(repo, "config", "user.name", "Nova School")
            self._git(repo, "config", "user.email", "nova@example.invalid")

            (repo / "README.md").write_text("one", encoding="utf-8")
            self._git(repo, "add", "README.md")
            self._git(repo, "commit", "-m", "Release Nova School Server v0.1.0")
            self._git(repo, "tag", "v0.1.0")

            (repo / "builder.txt").write_text("two", encoding="utf-8")
            self._git(repo, "add", "builder.txt")
            self._git(repo, "commit", "-m", "Add clean distribution release builder")

            (repo / "fix.txt").write_text("three", encoding="utf-8")
            self._git(repo, "add", "fix.txt")
            self._git(repo, "commit", "-m", "Fix LM Studio base URL normalization")

            history = build_release_history(repo)

            self.assertEqual(1, len(history.releases))
            self.assertEqual("v0.1.0", history.releases[0].tag)
            self.assertEqual(2, len(history.unreleased))
            self.assertEqual(["Added", "Fixed"], [entry.category for entry in history.unreleased])

            changelog = render_changelog(history)
            self.assertIn("# Changelog", changelog)
            self.assertIn("## Unreleased", changelog)
            self.assertIn("### Added", changelog)
            self.assertIn("### Fixed", changelog)
            self.assertIn("## v0.1.0 - ", changelog)
            self.assertIn("Release Nova School Server v0.1.0", changelog)

            release_notes = render_release_notes(history, "v0.1.0")
            self.assertIn("# Release v0.1.0", release_notes)
            self.assertIn("Release Nova School Server v0.1.0", release_notes)

    @staticmethod
    def _git(repo: Path, *args: str) -> None:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise AssertionError(result.stderr or result.stdout or f"git {' '.join(args)} failed")


if __name__ == "__main__":
    unittest.main()

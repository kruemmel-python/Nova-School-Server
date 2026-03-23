from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class ReleaseCommit:
    full_hash: str
    short_hash: str
    subject: str
    date: str
    category: str


@dataclass(slots=True)
class ReleaseVersion:
    tag: str
    date: str
    commits: list[ReleaseCommit]


@dataclass(slots=True)
class ReleaseHistory:
    unreleased: list[ReleaseCommit]
    releases: list[ReleaseVersion]


_CATEGORY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Release", ("release", "publish")),
    ("Added", ("add", "create", "introduce", "implement", "build")),
    ("Fixed", ("fix", "correct", "repair", "harden", "normalize", "resolve")),
    ("Changed", ("update", "change", "adjust", "refactor", "rename", "extend")),
)


def build_release_history(base_path: Path) -> ReleaseHistory:
    base_path = base_path.resolve(strict=False)
    tags = list_git_tags(base_path)
    releases: list[ReleaseVersion] = []
    for index, tag_info in enumerate(tags):
        tag = tag_info["tag"]
        previous_tag = tags[index + 1]["tag"] if index + 1 < len(tags) else ""
        revision_range = f"{previous_tag}..{tag}" if previous_tag else tag
        releases.append(
            ReleaseVersion(
                tag=tag,
                date=tag_info["date"],
                commits=list_git_commits(base_path, revision_range),
            )
        )
    latest_tag = tags[0]["tag"] if tags else ""
    unreleased_range = f"{latest_tag}..HEAD" if latest_tag else "HEAD"
    return ReleaseHistory(
        unreleased=list_git_commits(base_path, unreleased_range),
        releases=releases,
    )


def list_git_tags(base_path: Path) -> list[dict[str, str]]:
    output = _run_git(
        base_path,
        [
            "for-each-ref",
            "--sort=-creatordate",
            "--format=%(refname:strip=2)|%(creatordate:short)",
            "refs/tags",
        ],
    )
    tags: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        tag, date = line.split("|", 1)
        tags.append({"tag": tag.strip(), "date": date.strip()})
    return tags


def list_git_commits(base_path: Path, revision_range: str) -> list[ReleaseCommit]:
    output = _run_git(
        base_path,
        [
            "log",
            "--reverse",
            "--date=short",
            "--pretty=format:%H%x1f%h%x1f%ad%x1f%s",
            revision_range,
        ],
    )
    commits: list[ReleaseCommit] = []
    for line in output.splitlines():
        if not line.strip():
            continue
        full_hash, short_hash, date, subject = line.split("\x1f", 3)
        commits.append(
            ReleaseCommit(
                full_hash=full_hash,
                short_hash=short_hash,
                subject=subject.strip(),
                date=date.strip(),
                category=categorize_commit_subject(subject),
            )
        )
    return commits


def categorize_commit_subject(subject: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", subject.lower()).strip()
    first_word = normalized.split(" ", 1)[0] if normalized else ""
    for category, keywords in _CATEGORY_RULES:
        if first_word in keywords:
            return category
    for category, keywords in _CATEGORY_RULES:
        if any(keyword in normalized for keyword in keywords):
            return category
    return "Changed"


def render_changelog(history: ReleaseHistory) -> str:
    lines = [
        "# Changelog",
        "",
        "Dieses Changelog wird automatisch aus der Git-Historie erzeugt.",
        "",
        "## Unreleased",
        "",
    ]
    lines.extend(_render_commit_groups(history.unreleased))
    for release in history.releases:
        lines.extend(
            [
                "",
                f"## {release.tag} - {release.date}",
                "",
            ]
        )
        lines.extend(_render_commit_groups(release.commits))
    return "\n".join(lines).strip() + "\n"


def render_release_notes(history: ReleaseHistory, tag: str) -> str:
    release = next((entry for entry in history.releases if entry.tag == tag), None)
    if release is None:
        raise ValueError(f"unknown tag: {tag}")
    lines = [
        f"# Release {release.tag}",
        "",
        f"Veroeffentlicht am {release.date}.",
        "",
    ]
    lines.extend(_render_commit_groups(release.commits))
    return "\n".join(lines).strip() + "\n"


def write_changelog(base_path: Path, target_path: Path | None = None) -> Path:
    base_path = base_path.resolve(strict=False)
    history = build_release_history(base_path)
    output_path = (target_path or base_path / "CHANGELOG.md").resolve(strict=False)
    output_path.write_text(render_changelog(history), encoding="utf-8")
    return output_path


def write_release_notes(base_path: Path, tag: str, target_path: Path) -> Path:
    base_path = base_path.resolve(strict=False)
    history = build_release_history(base_path)
    output_path = target_path.resolve(strict=False)
    output_path.write_text(render_release_notes(history, tag), encoding="utf-8")
    return output_path


def _render_commit_groups(commits: Iterable[ReleaseCommit]) -> list[str]:
    grouped: dict[str, list[ReleaseCommit]] = {}
    for commit in commits:
        grouped.setdefault(commit.category, []).append(commit)
    if not grouped:
        return ["- Keine Eintraege."]
    lines: list[str] = []
    for category in ("Release", "Added", "Fixed", "Changed"):
        entries = grouped.get(category, [])
        if not entries:
            continue
        lines.append(f"### {category}")
        lines.append("")
        for commit in entries:
            lines.append(f"- {commit.subject} (`{commit.short_hash}`)")
        lines.append("")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def _run_git(base_path: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=base_path,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Generate changelog and release notes from the git history.")
    parser.add_argument("base_path", nargs="?", default=".", help="Projektwurzel")
    parser.add_argument("--changelog-path", default="CHANGELOG.md", help="Pfad fuer das CHANGELOG")
    parser.add_argument("--notes-tag", default="", help="Optionales Tag fuer Release-Notes")
    parser.add_argument("--notes-path", default="", help="Optionaler Ausgabepfad fuer Release-Notes")
    args = parser.parse_args()

    base_path = Path(args.base_path)
    changelog_path = Path(args.changelog_path)
    if not changelog_path.is_absolute():
        changelog_path = base_path / changelog_path
    written = write_changelog(base_path, changelog_path)
    print(written)

    if args.notes_tag:
        notes_path = Path(args.notes_path) if args.notes_path else base_path / f"release-notes-{args.notes_tag}.md"
        if not notes_path.is_absolute():
            notes_path = base_path / notes_path
        notes_written = write_release_notes(base_path, args.notes_tag, notes_path)
        print(notes_written)


if __name__ == "__main__":
    main()

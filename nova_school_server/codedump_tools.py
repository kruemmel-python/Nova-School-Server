from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
import zipfile


@dataclass(slots=True)
class DumpConfig:
    profile: str = "standard"
    allowed_extensions: set[str] = field(
        default_factory=lambda: {
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".cpp",
            ".c",
            ".h",
            ".hpp",
            ".java",
            ".rs",
            ".go",
            ".html",
            ".css",
            ".scss",
            ".json",
            ".md",
            ".txt",
            ".sh",
            ".bat",
            ".cmd",
            ".ps1",
            ".yaml",
            ".yml",
            ".toml",
            ".ini",
            ".cfg",
            ".conf",
            ".sql",
        }
    )
    allowed_filenames: set[str] = field(
        default_factory=lambda: {
            "Dockerfile",
            "Makefile",
            "README",
            "README.md",
            "requirements.txt",
            ".gitignore",
            ".dockerignore",
        }
    )
    ignore_names: tuple[str, ...] = (
        "__pycache__",
        ".git",
        "node_modules",
        ".venv",
        "venv",
        "dist",
        "build",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".idea",
        ".vscode",
        ".nova",
    )
    ignore_prefixes: tuple[str, ...] = (
        "data",
    )
    max_file_size: int = 200_000
    encoding: str = "utf-8"
    fallback_encoding: str = "latin-1"
    skipped_preview_limit: int = 40


CONFIG = DumpConfig()
PROFILE_NAMES = ("compact", "standard", "deep")


@dataclass(slots=True)
class DumpEntry:
    path: str
    language: str
    size: int
    status: str
    content: str


@dataclass(slots=True)
class DumpResult:
    source_name: str
    source_kind: str
    source_path: str
    entries: list[DumpEntry]
    ignored_paths: list[str]
    non_code_paths: list[str]


LANGUAGE_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "jsx",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".java": "java",
    ".rs": "rust",
    ".go": "go",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".json": "json",
    ".md": "markdown",
    ".txt": "text",
    ".sh": "bash",
    ".bat": "bat",
    ".cmd": "bat",
    ".ps1": "powershell",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".ini": "ini",
    ".cfg": "ini",
    ".conf": "ini",
    ".sql": "sql",
}


def is_ignored(path: str, config: DumpConfig, *, output_path: str | None = None) -> bool:
    normalized = path.replace("\\", "/").strip("/")
    folded = normalized.casefold()
    output_folded = output_path.replace("\\", "/").strip("/").casefold() if output_path else None
    if output_folded and folded == output_folded:
        return True
    if _is_dump_artifact(normalized):
        return True
    parts = [part.casefold() for part in Path(normalized).parts]
    if any(part in {name.casefold() for name in config.ignore_names} for part in parts):
        return True
    for prefix in config.ignore_prefixes:
        candidate = prefix.replace("\\", "/").strip("/").casefold()
        if folded == candidate or folded.startswith(candidate + "/"):
            return True
    return False


def is_code_file(path: str, config: DumpConfig) -> bool:
    candidate = Path(path)
    suffix = candidate.suffix.lower()
    return suffix in config.allowed_extensions or candidate.name in config.allowed_filenames


def detect_language(path: str) -> str:
    candidate = Path(path)
    return LANGUAGE_MAP.get(candidate.suffix.lower(), "text")


def generate_tree(file_paths: list[str]) -> str:
    tree: dict[str, dict] = {}
    for path in file_paths:
        current = tree
        for part in Path(path).parts:
            current = current.setdefault(part, {})

    def render(node: dict[str, dict], prefix: str = "") -> list[str]:
        lines: list[str] = []
        items = sorted(node.items(), key=lambda item: item[0].casefold())
        for index, (name, child) in enumerate(items):
            connector = "└── " if index == len(items) - 1 else "├── "
            lines.append(f"{prefix}{connector}{name}")
            extension = "    " if index == len(items) - 1 else "│   "
            lines.extend(render(child, prefix + extension))
        return lines

    return "\n".join(render(tree))


def dump_zip_to_markdown(zip_path: str | Path, output_md: str | Path, config: DumpConfig = CONFIG) -> None:
    dump_target_to_markdown(zip_path, output_md, config=config)


def dump_target_to_markdown(target: str | Path, output_md: str | Path, config: DumpConfig = CONFIG) -> Path:
    target_path = Path(target)
    output_path = Path(output_md)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if target_path.is_dir():
        result = collect_directory_dump(target_path, config=config, output_path=output_path)
    elif target_path.is_file() and target_path.suffix.lower() == ".zip":
        result = collect_zip_dump(target_path, config=config, output_path=output_path)
    else:
        raise FileNotFoundError(f"Unbekannter Dump-Input: {target_path}")

    output_path.write_text(render_dump_markdown(result, config=config), encoding="utf-8")
    return output_path


def collect_directory_dump(project_root: Path, *, config: DumpConfig = CONFIG, output_path: Path | None = None) -> DumpResult:
    entries: list[DumpEntry] = []
    ignored_paths: list[str] = []
    non_code_paths: list[str] = []
    output_resolved = output_path.resolve(strict=False) if output_path is not None else None
    output_relative = None
    if output_path is not None:
        try:
            output_relative = output_path.resolve(strict=False).relative_to(project_root.resolve(strict=False)).as_posix()
        except Exception:
            output_relative = None
    for path in sorted(project_root.rglob("*"), key=lambda item: item.as_posix().casefold()):
        if not path.is_file():
            continue
        if output_resolved is not None and path.resolve(strict=False) == output_resolved:
            ignored_paths.append(path.relative_to(project_root).as_posix())
            continue
        rel_path = path.relative_to(project_root).as_posix()
        if is_ignored(rel_path, config, output_path=output_relative):
            ignored_paths.append(rel_path)
            continue
        if not is_code_file(rel_path, config):
            non_code_paths.append(rel_path)
            continue
        entries.append(_entry_from_path(path, rel_path, config))
    return DumpResult(
        source_name=project_root.name,
        source_kind="directory",
        source_path=str(project_root),
        entries=entries,
        ignored_paths=ignored_paths,
        non_code_paths=non_code_paths,
    )


def collect_zip_dump(zip_path: Path, *, config: DumpConfig = CONFIG, output_path: Path | None = None) -> DumpResult:
    entries: list[DumpEntry] = []
    ignored_paths: list[str] = []
    non_code_paths: list[str] = []
    output_name = output_path.name if output_path is not None else None
    with zipfile.ZipFile(zip_path, "r") as archive:
        files = [info for info in archive.infolist() if not info.is_dir()]
        for info in sorted(files, key=lambda item: item.filename.casefold()):
            rel_path = info.filename.replace("\\", "/").strip("/")
            if is_ignored(rel_path, config, output_path=output_name):
                ignored_paths.append(rel_path)
                continue
            if not is_code_file(rel_path, config):
                non_code_paths.append(rel_path)
                continue
            entries.append(_entry_from_zip(archive, info, config))
    return DumpResult(
        source_name=zip_path.stem,
        source_kind="zip",
        source_path=str(zip_path),
        entries=entries,
        ignored_paths=ignored_paths,
        non_code_paths=non_code_paths,
    )


def render_dump_markdown(result: DumpResult, *, config: DumpConfig = CONFIG) -> str:
    lines = [
        f"# Code Dump: {result.source_name}",
        "",
        "## Uebersicht",
        "",
        f"- Quelle: `{result.source_path}`",
        f"- Typ: `{result.source_kind}`",
        f"- Profil: `{config.profile}`",
        f"- Enthaltene Dateien: `{len(result.entries)}`",
        f"- Ignorierte Dateien/Pfade: `{len(result.ignored_paths)}`",
        f"- Nicht-Code-Dateien: `{len(result.non_code_paths)}`",
        f"- Max. Dateigroesse pro Abschnitt: `{config.max_file_size}` Bytes",
        "",
    ]

    if result.ignored_paths:
        lines.extend(
            [
                "## Ignorierte Bereiche",
                "",
            ]
        )
        for label, count in _summarize_paths(result.ignored_paths, config=config)[: config.skipped_preview_limit]:
            lines.append(f"- `{label}`: `{count}` Dateien")
        lines.append("")

    lines.extend(
        [
            "## Projektstruktur",
            "",
            "```text",
            generate_tree([entry.path for entry in result.entries]) if result.entries else "[keine passenden Dateien gefunden]",
            "```",
            "",
            "## Dateien",
            "",
        ]
    )

    for entry in result.entries:
        lines.extend(
            [
                f"### `{entry.path}`",
                "",
                f"- Sprache: `{entry.language or 'text'}`",
                f"- Groesse: `{entry.size}` Bytes",
                f"- Status: `{entry.status}`",
                "",
                f"```{entry.language}",
                entry.content.rstrip(),
                "```",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _entry_from_path(path: Path, relative_path: str, config: DumpConfig) -> DumpEntry:
    size = path.stat().st_size
    if size > config.max_file_size:
        return DumpEntry(
            path=relative_path,
            language=detect_language(relative_path),
            size=size,
            status="skipped-too-large",
            content=f"[SKIPPED: file too large ({size} bytes)]",
        )
    try:
        raw = path.read_bytes()
    except Exception as exc:
        return DumpEntry(
            path=relative_path,
            language=detect_language(relative_path),
            size=size,
            status="read-error",
            content=f"[ERROR READING FILE: {exc}]",
        )
    return _entry_from_bytes(relative_path, raw, size, config)


def _entry_from_zip(archive: zipfile.ZipFile, info: zipfile.ZipInfo, config: DumpConfig) -> DumpEntry:
    relative_path = info.filename.replace("\\", "/").strip("/")
    if info.file_size > config.max_file_size:
        return DumpEntry(
            path=relative_path,
            language=detect_language(relative_path),
            size=info.file_size,
            status="skipped-too-large",
            content=f"[SKIPPED: file too large ({info.file_size} bytes)]",
        )
    try:
        with archive.open(info) as handle:
            raw = handle.read()
    except Exception as exc:
        return DumpEntry(
            path=relative_path,
            language=detect_language(relative_path),
            size=info.file_size,
            status="read-error",
            content=f"[ERROR READING FILE: {exc}]",
        )
    return _entry_from_bytes(relative_path, raw, info.file_size, config)


def _entry_from_bytes(relative_path: str, raw: bytes, size: int, config: DumpConfig) -> DumpEntry:
    if b"\x00" in raw:
        return DumpEntry(
            path=relative_path,
            language=detect_language(relative_path),
            size=size,
            status="skipped-binary",
            content="[SKIPPED: binary content detected]",
        )
    try:
        content = raw.decode(config.encoding)
    except UnicodeDecodeError:
        content = raw.decode(config.fallback_encoding, errors="replace")
    return DumpEntry(
        path=relative_path,
        language=detect_language(relative_path),
        size=size,
        status="included",
        content=content,
    )


def _summarize_paths(paths: Iterable[str], *, config: DumpConfig) -> list[tuple[str, int]]:
    buckets: dict[str, int] = {}
    for path in paths:
        label = _summary_label_for_path(path, config=config)
        buckets[label] = buckets.get(label, 0) + 1
    return sorted(buckets.items(), key=lambda item: (-item[1], item[0].casefold()))


def _summary_label_for_path(path: str, *, config: DumpConfig) -> str:
    normalized = path.replace("\\", "/").strip("/")
    folded = normalized.casefold()
    for prefix in config.ignore_prefixes:
        candidate = prefix.replace("\\", "/").strip("/").casefold()
        if folded == candidate or folded.startswith(candidate + "/"):
            return prefix.replace("\\", "/").strip("/") or "."
    parts = Path(normalized).parts
    ignored_names = {name.casefold(): name for name in config.ignore_names}
    for part in parts:
        if part.casefold() in ignored_names:
            return ignored_names[part.casefold()]
    if _is_dump_artifact(normalized):
        return "codedump-artifacts"
    return parts[0] if parts else normalized or "."


def _is_dump_artifact(path: str) -> bool:
    name = Path(path).name.casefold()
    return (name.startswith("codedump") and name.endswith(".md")) or name.endswith(".codedump.md")


def default_output_path(target: str | Path) -> Path:
    target_path = Path(target)
    if target_path.is_dir():
        return target_path / "CODEDUMP.md"
    return target_path.with_suffix(".codedump.md")


def config_for_profile(profile: str, *, max_file_size: int | None = None) -> DumpConfig:
    normalized = (profile or "standard").strip().lower()
    if normalized not in PROFILE_NAMES:
        raise ValueError(f"Unbekanntes Dump-Profil: {profile}")

    config = DumpConfig(profile=normalized)
    if normalized == "compact":
        config.ignore_prefixes = ("data", "docs", "wiki", "nova_school_server/tests")
        config.max_file_size = 80_000
        config.skipped_preview_limit = 12
    elif normalized == "deep":
        config.ignore_prefixes = ("data",)
        config.max_file_size = 350_000
        config.skipped_preview_limit = 60
    if max_file_size is not None:
        config.max_file_size = max(1, int(max_file_size))
    return config


def default_output_path_for_profile(target: str | Path, profile: str) -> Path:
    normalized = (profile or "standard").strip().lower()
    target_path = Path(target)
    if target_path.is_dir():
        if normalized == "standard":
            return target_path / "CODEDUMP.md"
        return target_path / f"CODEDUMP.{normalized}.md"
    if normalized == "standard":
        return target_path.with_suffix(".codedump.md")
    return target_path.with_name(f"{target_path.stem}.{normalized}.codedump.md")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Erzeugt einen Markdown-Code-Dump aus einem Projektordner oder einer ZIP-Datei.")
    parser.add_argument("target", nargs="?", default=".", help="Projektordner oder ZIP-Datei. Standard: aktueller Ordner.")
    parser.add_argument("-o", "--output", help="Zielpfad fuer die Markdown-Datei. Standard: CODEDUMP.md im Projektordner.")
    parser.add_argument(
        "--profile",
        choices=PROFILE_NAMES,
        default="standard",
        help="Dump-Profil: compact fuer kleine KI-Prompts, standard fuer den Regelfall, deep fuer umfassendere Analysen.",
    )
    parser.add_argument("--max-file-size", type=int, default=None, help="Maximale Dateigroesse pro Datei in Bytes.")
    args = parser.parse_args()

    config = config_for_profile(args.profile, max_file_size=args.max_file_size)
    output_path = Path(args.output) if args.output else default_output_path_for_profile(args.target, args.profile)
    target_path = Path(args.target)
    written = dump_target_to_markdown(target_path, output_path, config=config)
    print(f"Code-Dump geschrieben: {written}")

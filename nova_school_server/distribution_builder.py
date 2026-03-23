from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


SKIP_NAMES = {
    ".git",
    ".github",
    ".pytest_cache",
    "__pycache__",
    ".nova",
    "node_modules",
    "dist",
    "build",
}
SKIP_FILE_SUFFIXES = {".pyc", ".pyo", ".pyd", ".db", ".shm", ".wal", ".zip"}
SKIP_FILE_NAMES = {
    "analysis_dump.md",
    "Projektcode_analysis_dump.md",
    "info.png",
}


@dataclass(slots=True)
class DistributionBuildResult:
    version: str
    archive_path: Path
    staging_root: Path


def detect_project_version(base_path: Path) -> str:
    pyproject = (base_path / "pyproject.toml").read_text(encoding="utf-8")
    for line in pyproject.splitlines():
        stripped = line.strip()
        if stripped.startswith("version = "):
            return stripped.split("=", 1)[1].strip().strip("\"'")
    return "0.1.0"


def build_distribution_archive(base_path: Path, output_dir: Path | None = None, version: str | None = None) -> DistributionBuildResult:
    base_path = base_path.resolve(strict=False)
    version_text = version or detect_project_version(base_path)
    output_dir = (output_dir or base_path).resolve(strict=False)
    package_name = f"Nova-School-Server-v{version_text}-distribution"
    archive_path = output_dir / f"{package_name}.zip"

    with tempfile.TemporaryDirectory(prefix="nova-school-distribution-") as tmp:
        staging_root = Path(tmp) / package_name
        staging_root.mkdir(parents=True, exist_ok=True)
        _copy_project_tree(base_path, staging_root)
        _create_distribution_scaffold(staging_root, version_text)
        if archive_path.exists():
            archive_path.unlink()
        _zip_tree(staging_root, archive_path)
    return DistributionBuildResult(version=version_text, archive_path=archive_path, staging_root=Path(package_name))


def _copy_project_tree(source_root: Path, target_root: Path) -> None:
    for item in source_root.iterdir():
        if _should_skip_root_entry(item):
            continue
        destination = target_root / item.name
        if item.is_dir():
            _copy_directory(item, destination)
        elif item.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def _copy_directory(source_dir: Path, target_dir: Path) -> None:
    for item in source_dir.iterdir():
        if _should_skip_entry(item):
            continue
        destination = target_dir / item.name
        if item.is_dir():
            _copy_directory(item, destination)
        elif item.is_file():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, destination)


def _should_skip_root_entry(path: Path) -> bool:
    if path.name == "data":
        return True
    return _should_skip_entry(path)


def _should_skip_entry(path: Path) -> bool:
    if path.name in SKIP_NAMES:
        return True
    if path.is_file():
        if path.name in SKIP_FILE_NAMES:
            return True
        if any(path.name.endswith(marker) for marker in ("_analysis_dump.md", ".codedump.md")):
            return True
        if path.suffix.lower() in SKIP_FILE_SUFFIXES:
            return True
    return False


def _create_distribution_scaffold(staging_root: Path, version: str) -> None:
    _ensure_placeholder(staging_root / "data" / "workspaces" / "users" / ".gitkeep")
    _ensure_placeholder(staging_root / "data" / "workspaces" / "groups" / ".gitkeep")
    _ensure_placeholder(staging_root / "data" / "reference_library" / "packs" / ".gitkeep")
    _ensure_placeholder(staging_root / "data" / "reference_library" / "index" / ".gitkeep")
    _ensure_placeholder(staging_root / "data" / "public_shares" / ".gitkeep")
    _ensure_placeholder(staging_root / "data" / "exports" / ".gitkeep")
    _ensure_placeholder(staging_root / "data" / "review_submissions" / ".gitkeep")
    _ensure_placeholder(staging_root / "data" / "worker_dispatch" / "artifacts" / ".gitkeep")
    _ensure_placeholder(staging_root / "data" / "container_build" / ".gitkeep")
    _ensure_placeholder(staging_root / "data" / "python_package_cache" / ".gitkeep")
    _ensure_placeholder(staging_root / "data" / "docs" / ".gitkeep")

    server_config_example = {
        "host": "0.0.0.0",
        "port": 8877,
        "session_ttl_seconds": 43200,
        "run_timeout_seconds": 20,
        "live_run_timeout_seconds": 300,
        "tenant_id": "nova-school",
        "school_name": "Nova School Server",
        "nova_shell_path": "",
    }
    (staging_root / "server_config.json.example").write_text(
        json.dumps(server_config_example, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    manifest = {
        "package_type": "distribution",
        "version": version,
        "includes_runtime_data": False,
        "includes_reference_mirrors": False,
        "includes_workspaces": False,
    }
    (staging_root / "release_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    notes = """# Nova School Server Distribution

Dieses Paket ist fuer Schulen als sauberes Distributionspaket gedacht.

Enthaelt:
- vollstaendigen Quellcode
- Startskripte fuer Windows und Linux
- Wiki- und Produktdokumentation
- leere Datenordner fuer den Erststart
- Beispielkonfiguration `server_config.json.example`

Nicht enthalten:
- lokale Datenbanken
- bestehende Benutzer- oder Projektdaten
- Laufzeit-Workspaces
- PKI-/Secret-Artefakte
- lokale Referenz-Mirror-Caches

Start:
- Windows: `start_server.ps1`
- Linux: `start_server.sh`

Vor dem ersten produktiven Einsatz:
1. `requirements.txt` installieren
2. `server_config.json.example` nach `server_config.json` kopieren und anpassen
3. optionale Offline-Referenzbibliotheken importieren
4. LM Studio und Container-Runtime nach Bedarf konfigurieren
"""
    (staging_root / "DISTRIBUTION_README.md").write_text(notes, encoding="utf-8")


def _ensure_placeholder(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")


def _zip_tree(root: Path, archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in sorted(_iter_files(root)):
            archive.write(file_path, file_path.relative_to(root.parent))


def _iter_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file():
            yield path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Build a clean Nova School Server distribution archive.")
    parser.add_argument("base_path", nargs="?", default=".", help="Projektwurzel")
    parser.add_argument("--output-dir", default=".", help="Zielordner fuer das Archiv")
    parser.add_argument("--version", default="", help="Optionale Versionsnummer")
    args = parser.parse_args()

    result = build_distribution_archive(
        Path(args.base_path),
        output_dir=Path(args.output_dir),
        version=args.version or None,
    )
    print(result.archive_path)


if __name__ == "__main__":
    main()

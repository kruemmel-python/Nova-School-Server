from __future__ import annotations

import shutil
from pathlib import Path


def copy_project_snapshot(project_root: Path, target_root: Path) -> list[str]:
    copied_files: list[str] = []
    target_root.mkdir(parents=True, exist_ok=True)
    for path in sorted(project_root.rglob("*"), key=lambda item: item.as_posix().lower()):
        relative = path.relative_to(project_root)
        if ".nova-school" in relative.parts:
            continue
        destination = target_root / relative
        if path.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        copied_files.append(relative.as_posix())
    return copied_files


def list_snapshot_files(snapshot_root: Path) -> list[str]:
    return [
        path.relative_to(snapshot_root).as_posix()
        for path in sorted(snapshot_root.rglob("*"), key=lambda item: item.as_posix().lower())
        if path.is_file()
    ]


def read_text_preview(snapshot_root: Path, preferred_path: str | None = None, max_chars: int = 3200) -> dict[str, str]:
    if preferred_path:
        candidate = snapshot_root / preferred_path
        if candidate.exists() and candidate.is_file():
            return {
                "path": preferred_path,
                "content": candidate.read_text(encoding="utf-8", errors="replace")[:max_chars],
            }
    for path in sorted(snapshot_root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if path.is_file():
            return {
                "path": path.relative_to(snapshot_root).as_posix(),
                "content": path.read_text(encoding="utf-8", errors="replace")[:max_chars],
            }
    return {"path": "", "content": ""}

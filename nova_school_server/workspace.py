from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .config import ServerConfig
from .templates import PROJECT_TEMPLATES


class WorkspaceManager:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        self.config.users_workspace_path.mkdir(parents=True, exist_ok=True)
        self.config.groups_workspace_path.mkdir(parents=True, exist_ok=True)

    def ensure_profile_folder(self, owner_type: str, owner_key: str) -> Path:
        root = self.owner_root(owner_type, owner_key)
        root.mkdir(parents=True, exist_ok=True)
        return root

    def owner_root(self, owner_type: str, owner_key: str) -> Path:
        safe_key = slugify(owner_key)
        if owner_type == "user":
            return self.config.users_workspace_path / safe_key
        if owner_type == "group":
            return self.config.groups_workspace_path / safe_key
        raise ValueError(f"unknown owner_type: {owner_type}")

    def project_root(self, project: dict[str, Any]) -> Path:
        return self.owner_root(str(project["owner_type"]), str(project["owner_key"])) / "projects" / slugify(str(project["slug"]))

    def materialize_project(self, project: dict[str, Any]) -> Path:
        template = PROJECT_TEMPLATES[str(project["template"])]
        project_root = self.project_root(project)
        project_root.mkdir(parents=True, exist_ok=True)
        meta_root = project_root / ".nova-school"
        meta_root.mkdir(parents=True, exist_ok=True)

        for relative_path, content in dict(template.get("files", {})).items():
            target = project_root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(str(content), encoding="utf-8")

        notebook_path = meta_root / "notebook.json"
        if not notebook_path.exists():
            notebook = list(template.get("notebook", []))
            notebook_path.write_text(json.dumps(notebook, ensure_ascii=False, indent=2), encoding="utf-8")
        return project_root

    def list_tree(self, project: dict[str, Any]) -> list[dict[str, Any]]:
        root = self.project_root(project)
        if not root.exists():
            return []
        entries: list[dict[str, Any]] = []
        for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower()):
            if ".nova-school" in path.parts:
                continue
            relative_path = path.relative_to(root).as_posix()
            stat = path.stat()
            entries.append(
                {
                    "path": relative_path,
                    "name": path.name,
                    "kind": "directory" if path.is_dir() else "file",
                    "size": stat.st_size if path.is_file() else None,
                    "modified_at": stat.st_mtime,
                }
            )
        return entries

    def read_file(self, project: dict[str, Any], relative_path: str) -> dict[str, Any]:
        target = self.resolve_project_path(project, relative_path)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(relative_path)
        return {
            "path": relative_path,
            "content": target.read_text(encoding="utf-8"),
            "absolute_path": str(target),
        }

    def write_file(self, project: dict[str, Any], relative_path: str, content: str) -> dict[str, Any]:
        target = self.resolve_project_path(project, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": relative_path, "absolute_path": str(target), "size": len(content.encode("utf-8"))}

    def load_notebook(self, project: dict[str, Any]) -> list[dict[str, Any]]:
        notebook_path = self._notebook_path(project)
        if not notebook_path.exists():
            return []
        cells = list(json.loads(notebook_path.read_text(encoding="utf-8")))
        normalized = [self._normalize_legacy_notebook_cell(cell) for cell in cells]
        if normalized != cells:
            notebook_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2), encoding="utf-8")
        return normalized

    def save_notebook(self, project: dict[str, Any], cells: list[dict[str, Any]]) -> list[dict[str, Any]]:
        notebook_path = self._notebook_path(project)
        notebook_path.parent.mkdir(parents=True, exist_ok=True)
        notebook_path.write_text(json.dumps(cells, ensure_ascii=False, indent=2), encoding="utf-8")
        return cells

    def resolve_project_path(self, project: dict[str, Any], relative_path: str) -> Path:
        root = self.project_root(project).resolve(strict=False)
        target = (root / relative_path).resolve(strict=False)
        if not target.is_relative_to(root):
            raise ValueError(f"illegal project path: {relative_path}")
        return target

    def _notebook_path(self, project: dict[str, Any]) -> Path:
        return self.project_root(project) / ".nova-school" / "notebook.json"

    @staticmethod
    def _normalize_legacy_notebook_cell(cell: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(cell)
        code = normalized.get("code")
        if not isinstance(code, str):
            return normalized
        legacy_code_map = {
            "numbers = [1, 2, 3, 4]\\nprint(sum(numbers))\\n": "numbers = [1, 2, 3, 4]\nprint(sum(numbers))\n",
            "const values = [3, 5, 8];\\nconsole.log(values.reduce((sum, value) => sum + value, 0));\\n": "const values = [3, 5, 8];\nconsole.log(values.reduce((sum, value) => sum + value, 0));\n",
        }
        normalized["code"] = legacy_code_map.get(code, code)
        return normalized


def slugify(value: str) -> str:
    lowered = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", lowered)
    normalized = normalized.strip("-")
    return normalized or "workspace"

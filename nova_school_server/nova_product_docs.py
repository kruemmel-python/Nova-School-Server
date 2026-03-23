from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .permissions import PERMISSION_DEFINITIONS, ROLE_DEFAULTS


class NovaSchoolProductDocsBuilder:
    def __init__(self, source_root: Path, pack_root: Path) -> None:
        self.source_root = source_root
        self.pack_root = pack_root
        self.site_root = self.pack_root / "site"
        self.manifest_path = self.pack_root / "manifest.json"

    def ensure_built(self) -> bool:
        if not self._has_sources():
            return self.site_root.exists()
        if self.is_stale():
            self.build()
        return self.site_root.exists()

    def is_stale(self) -> bool:
        if not self._has_sources():
            return False
        if not self.site_root.exists() or not self.manifest_path.exists():
            return True
        try:
            payload = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except Exception:
            return True
        return payload.get("source_signature") != self._source_signature()

    def build(self) -> None:
        if not self._has_sources():
            return
        self.pack_root.mkdir(parents=True, exist_ok=True)
        if self.site_root.exists():
            shutil.rmtree(self.site_root)
        self.site_root.mkdir(parents=True, exist_ok=True)

        documents: list[dict[str, str]] = []
        for source_path in self._source_files():
            content = self._expand_tokens(source_path.read_text(encoding="utf-8"))
            title = self._extract_title(content, source_path)
            summary = self._extract_summary(content)
            target_path = self.site_root / source_path.name
            target_path.write_text(content.rstrip() + "\n", encoding="utf-8")
            documents.append({"filename": source_path.name, "title": title, "summary": summary})

        index_content = self._build_index(documents)
        (self.site_root / "index.md").write_text(index_content.rstrip() + "\n", encoding="utf-8")
        self.manifest_path.write_text(
            json.dumps(
                {
                    "builder": "nova-school-product-docs",
                    "source_root": str(self.source_root),
                    "source_signature": self._source_signature(),
                    "document_count": len(documents) + 1,
                    "documents": documents,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def _build_index(self, documents: list[dict[str, str]]) -> str:
        lines = [
            "# Nova School Produktdokumentation",
            "",
            "Diese Referenz ist die offizielle First-Party-Dokumentation des Nova School Servers.",
            "Sie beschreibt Rollen, Rechte, Arbeitsablaeufe, Sicherheit, Unterrichtsbegleitung und Betrieb.",
            "",
            "## Was diese Bibliothek abdeckt",
            "",
            "- Rollenmodell fuer Schueler, Lehrkraefte und Administration",
            "- Benutzer, Gruppen, Rechte, Moderation und Audit-Nachweise",
            "- Projekte, Workspaces, Profilordner, Gruppenordner und Dateistruktur",
            "- Editor, Notebook-Zellen, Live-Terminal, PTY und Programmeingaben",
            "- Offline-Referenzbibliothek, LM Studio und sokratischer Mentor",
            "- Chat, Peer Review, Lernanalyse, Playground, Deployments und Betrieb",
            "",
            "## Dokumente",
            "",
            "| Dokument | Schwerpunkt |",
            "| --- | --- |",
        ]
        for item in documents:
            target = f"/reference?area=nova-school&doc={item['filename']}"
            lines.append(f"| [{item['title']}]({target}) | {item['summary']} |")
        lines.extend(
            [
                "",
                "## Verwandte Bereiche",
                "",
                "- [Bedienungsanleitung fuer Rollen](/manual)",
                "- [Offline Referenzbibliothek fuer Programmiersprachen](/reference?area=python)",
                "- [Nova School Oberflaeche](/)",
            ]
        )
        return "\n".join(lines)

    def _expand_tokens(self, content: str) -> str:
        return (
            content.replace("{{PERMISSION_TABLE}}", self._permission_table())
            .replace("{{ROLE_DEFAULTS_TABLE}}", self._role_defaults_table())
        )

    def _permission_table(self) -> str:
        lines = [
            "| Key | Bereich | Beschreibung |",
            "| --- | --- | --- |",
        ]
        for item in PERMISSION_DEFINITIONS:
            lines.append(f"| `{item['key']}` | {item['category']} | {item['label']} |")
        return "\n".join(lines)

    def _role_defaults_table(self) -> str:
        lines = [
            "| Recht | Student | Teacher | Admin |",
            "| --- | --- | --- | --- |",
        ]
        for item in PERMISSION_DEFINITIONS:
            key = item["key"]
            lines.append(
                f"| `{key}` | {self._bool_label(ROLE_DEFAULTS['student'].get(key, False))} | "
                f"{self._bool_label(ROLE_DEFAULTS['teacher'].get(key, False))} | "
                f"{self._bool_label(ROLE_DEFAULTS['admin'].get(key, False))} |"
            )
        return "\n".join(lines)

    @staticmethod
    def _bool_label(value: bool) -> str:
        return "Ja" if value else "Nein"

    def _has_sources(self) -> bool:
        return self.source_root.exists() and any(self._source_files())

    def _source_files(self) -> list[Path]:
        return sorted(
            (path for path in self.source_root.glob("*.md") if path.is_file()),
            key=lambda item: item.name.lower(),
        )

    def _source_signature(self) -> dict[str, Any]:
        files = self._source_files()
        latest_mtime_ns = max((path.stat().st_mtime_ns for path in files), default=0)
        total_size = sum(path.stat().st_size for path in files)
        return {
            "file_count": len(files),
            "latest_mtime_ns": latest_mtime_ns,
            "total_size": total_size,
        }

    @staticmethod
    def _extract_title(content: str, path: Path) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return path.stem.replace("_", " ").strip()

    @staticmethod
    def _extract_summary(content: str) -> str:
        for line in content.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("|") or stripped.startswith("```"):
                continue
            return stripped[:160]
        return "Nova School Referenzdokument."


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    builder = NovaSchoolProductDocsBuilder(
        source_root=project_root / "docs" / "nova_school",
        pack_root=project_root / "data" / "reference_library" / "packs" / "nova-school",
    )
    builder.build()


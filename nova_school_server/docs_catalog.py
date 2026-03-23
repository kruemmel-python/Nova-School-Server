from __future__ import annotations

from pathlib import Path

from .templates import OFFLINE_DOCS


class DocumentationCatalog:
    def __init__(self, docs_path: Path) -> None:
        self.docs_path = docs_path
        self.docs_path.mkdir(parents=True, exist_ok=True)

    def ensure_seed_docs(self) -> None:
        for slug, payload in OFFLINE_DOCS.items():
            target = self.docs_path / f"{slug}.md"
            if target.exists():
                continue
            target.write_text(str(payload["content"]), encoding="utf-8")

    def list_docs(self) -> list[dict[str, object]]:
        return [
            {
                "slug": slug,
                "title": payload["title"],
                "tags": list(payload.get("tags", [])),
                "path": str(self.docs_path / f"{slug}.md"),
            }
            for slug, payload in OFFLINE_DOCS.items()
        ]

    def get_doc(self, slug: str) -> dict[str, object]:
        if slug not in OFFLINE_DOCS:
            raise FileNotFoundError(f"documentation not found: {slug}")
        path = self.docs_path / f"{slug}.md"
        return {
            "slug": slug,
            "title": OFFLINE_DOCS[slug]["title"],
            "tags": list(OFFLINE_DOCS[slug].get("tags", [])),
            "content": path.read_text(encoding="utf-8"),
        }

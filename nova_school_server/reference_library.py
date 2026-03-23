from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from .nova_product_docs import NovaSchoolProductDocsBuilder
from .templates import OFFLINE_DOCS


DOCUMENT_SUFFIXES = {".html", ".htm", ".md", ".txt"}
INDEX_SCHEMA_VERSION = 2

CPP_PAGE_TITLE_FALLBACKS: dict[str, str] = {
    "01_language/language.md": "C++ Language",
    "02_containers/container.md": "Containers Library",
    "03_strings/string.md": "Strings Library",
    "04_algorithms/algorithm.md": "Algorithms Library",
    "05_memory/memory.md": "Memory Management Library",
    "06_threads/thread.md": "Concurrency Support Library",
    "index.md": "C++ Offline Documentation",
}


REFERENCE_PACKS: dict[str, dict[str, str]] = {
    "python": {"label": "Python", "source_label": "Python Documentation", "source_kind": "official"},
    "javascript": {"label": "JavaScript", "source_label": "ECMAScript / JavaScript Referenz", "source_kind": "primary"},
    "cpp": {"label": "C++", "source_label": "C++ Referenz", "source_kind": "canonical"},
    "java": {"label": "Java", "source_label": "Java Documentation", "source_kind": "official"},
    "rust": {"label": "Rust", "source_label": "The Rust Documentation", "source_kind": "official"},
    "html-css": {"label": "HTML und CSS", "source_label": "HTML/CSS Referenz", "source_kind": "primary"},
    "node-npm": {"label": "Node.js und npm", "source_label": "Node.js / npm Docs", "source_kind": "official"},
    "web-frontend": {"label": "Web Frontend", "source_label": "Frontend Referenz", "source_kind": "canonical"},
    "nova-school": {"label": "Nova School", "source_label": "Nova School Produktdokumentation", "source_kind": "product"},
}


class ReferenceLibraryService:
    def __init__(self, library_root: Path, docs_source_root: Path | None = None) -> None:
        self.library_root = library_root
        self.packs_root = self.library_root / "packs"
        self.index_root = self.library_root / "index"
        self.packs_root.mkdir(parents=True, exist_ok=True)
        self.index_root.mkdir(parents=True, exist_ok=True)
        self.docs_source_root = docs_source_root or self._default_docs_source_root()
        self.nova_product_docs = (
            NovaSchoolProductDocsBuilder(self.docs_source_root, self._pack_root("nova-school"))
            if self.docs_source_root is not None
            else None
        )

    def catalog(self) -> list[dict[str, Any]]:
        return [self._catalog_entry(slug) for slug in REFERENCE_PACKS]

    def render_portal(self, *, area: str | None = None, doc_id: str | None = None, query: str = "") -> str:
        selected_area = area if area in REFERENCE_PACKS else next(iter(REFERENCE_PACKS))
        catalog = self.catalog()
        documents = self.documents(selected_area, limit=80)
        active_doc = self.resolve_document(selected_area, doc_id or "")
        if active_doc is None and documents:
            active_doc = self.resolve_document(selected_area, str(documents[0]["doc_id"]))
        selected_label = REFERENCE_PACKS[selected_area]["label"]
        results = self.search(query, area=selected_area if selected_area else None, limit=40) if query.strip() else []
        result_summary = (
            f"{len(results)} Treffer fuer {selected_label}"
            if query.strip()
            else f"{len(documents)} Dokumente in {selected_label}"
        )
        return self._render_shell(
            selected_area=selected_area,
            catalog=catalog,
            documents=documents,
            active_doc=active_doc,
            query=query,
            results=results,
            result_summary=result_summary,
        )

    def resolve_asset(self, area: str, relative_path: str) -> Path:
        if area not in REFERENCE_PACKS:
            raise FileNotFoundError("Unbekannter Referenzbereich.")
        self._ensure_managed_pack(area)
        root = self._content_root(area)
        if root is None:
            raise FileNotFoundError("Referenzdatei nicht gefunden.")
        root = root.resolve(strict=False)
        target = (root / relative_path).resolve(strict=False)
        if not target.is_relative_to(root):
            raise PermissionError("Ungueltiger Referenzpfad.")
        if not target.exists() or not target.is_file():
            raise FileNotFoundError("Referenzdatei nicht gefunden.")
        return target

    def documents(self, area: str, limit: int = 80) -> list[dict[str, Any]]:
        docs = self._load_documents(area)
        return docs[: max(1, int(limit))]

    def resolve_document(self, area: str, doc_id: str) -> dict[str, Any] | None:
        docs = self._load_documents(area)
        if not docs:
            return None
        wanted = (doc_id or "").strip()
        if not wanted:
            return docs[0]
        wanted_folded = wanted.casefold()
        return next((item for item in docs if str(item["doc_id"]).casefold() == wanted_folded), docs[0])

    def search(self, query: str, *, area: str | None = None, limit: int = 40) -> list[dict[str, Any]]:
        terms = [item for item in re.findall(r"[a-z0-9\-\._]+", query.lower()) if item]
        if not terms:
            return []
        results: list[dict[str, Any]] = []
        areas = [area] if area in REFERENCE_PACKS else list(REFERENCE_PACKS)
        for slug in areas:
            for doc in self._load_documents(slug):
                haystack = f"{doc['title']} {doc.get('search_text') or ''}".lower()
                title_text = str(doc["title"]).lower()
                score = 0
                for term in terms:
                    if term in title_text:
                        score += 15
                    score += haystack.count(term)
                if score <= 0:
                    continue
                results.append(
                    {
                        "area": slug,
                        "area_label": REFERENCE_PACKS[slug]["label"],
                        "doc_id": doc["doc_id"],
                        "title": doc["title"],
                        "score": score,
                        "snippet": self._snippet(doc.get("search_text") or "", terms),
                        "status": doc["status"],
                    }
                )
        results.sort(key=lambda item: (-int(item["score"]), str(item["area_label"]).lower(), str(item["title"]).lower()))
        return results[: max(1, int(limit))]

    def _catalog_entry(self, slug: str) -> dict[str, Any]:
        self._ensure_managed_pack(slug)
        docs = self._load_documents(slug)
        installed = self._has_mirrored_pack(slug)
        status = self._status_for_slug(slug, installed)
        return {
            "slug": slug,
            "label": REFERENCE_PACKS[slug]["label"],
            "source_label": REFERENCE_PACKS[slug]["source_label"],
            "source_kind": REFERENCE_PACKS[slug]["source_kind"],
            "status": status,
            "doc_count": len(docs),
            "install_path": str(self._pack_root(slug)),
        }

    def _load_documents(self, slug: str) -> list[dict[str, Any]]:
        self._ensure_managed_pack(slug)
        if self._has_mirrored_pack(slug):
            index_path = self._index_path(slug)
            if self._index_is_stale(slug):
                self._build_index(slug)
            try:
                payload = json.loads(index_path.read_text(encoding="utf-8"))
                docs = list(payload.get("documents") or [])
                if docs:
                    return docs
            except Exception:
                self._build_index(slug)
                payload = json.loads(index_path.read_text(encoding="utf-8"))
                docs = list(payload.get("documents") or [])
                if docs:
                    return docs
        return [self._builtin_document(slug)] if slug in OFFLINE_DOCS else []

    def _build_index(self, slug: str) -> None:
        site_root = self._content_root(slug)
        if site_root is None:
            self._index_path(slug).write_text(json.dumps({"meta": {}, "documents": []}, ensure_ascii=False, indent=2), encoding="utf-8")
            return
        signature = self._pack_signature(site_root)
        documents: list[dict[str, Any]] = []
        for path in self._iter_doc_files(site_root):
            rel_path = path.relative_to(site_root).as_posix()
            content = path.read_text(encoding="utf-8", errors="ignore")
            documents.append(self._build_document_entry(slug, path, rel_path, content))
        self._index_path(slug).write_text(
            json.dumps({"meta": signature, "documents": documents}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _builtin_document(self, slug: str) -> dict[str, Any]:
        payload = OFFLINE_DOCS[slug]
        content = str(payload["content"])
        return {
            "doc_id": "__builtin__",
            "title": str(payload["title"]),
            "rel_path": "",
            "search_text": self._markdown_plain_text(content),
            "summary": self._markdown_plain_text(content)[:260],
            "viewer": "builtin",
            "content_type": "markdown",
            "status": "starter",
            "content": content,
        }

    def _has_mirrored_pack(self, slug: str) -> bool:
        return self._content_root(slug) is not None

    def _pack_root(self, slug: str) -> Path:
        return self.packs_root / slug

    def _site_root(self, slug: str) -> Path:
        return self._pack_root(slug) / "site"

    def _index_path(self, slug: str) -> Path:
        return self.index_root / f"{slug}.json"

    def _content_root(self, slug: str) -> Path | None:
        site_root = self._site_root(slug)
        if self._contains_documents(site_root):
            return site_root
        pack_root = self._pack_root(slug)
        if self._contains_documents(pack_root):
            return pack_root
        return None

    def _contains_documents(self, root: Path) -> bool:
        if not root.exists() or not root.is_dir():
            return False
        return any(True for _ in self._iter_doc_files(root))

    def _iter_doc_files(self, root: Path) -> list[Path]:
        return [
            path
            for path in sorted(root.rglob("*"), key=lambda item: item.as_posix().lower())
            if path.is_file() and path.suffix.lower() in DOCUMENT_SUFFIXES
        ]

    def _build_document_entry(self, slug: str, path: Path, rel_path: str, content: str) -> dict[str, Any]:
        render_content = None
        prepared_content = content
        if slug == "cpp" and path.suffix.lower() == ".md":
            prepared_content = self._normalize_cpp_markdown(rel_path, content)
            render_content = prepared_content
        title, plain_text, doc_type = self._extract_document_data(path, prepared_content)
        entry = {
            "doc_id": rel_path,
            "title": title,
            "rel_path": rel_path,
            "search_text": plain_text[:80_000],
            "summary": plain_text[:260],
            "viewer": "iframe" if doc_type == "html" else "rendered",
            "content_type": doc_type,
            "status": self._status_for_slug(slug, installed=True),
        }
        if render_content is not None:
            entry["render_content"] = render_content
        return entry

    def _pack_signature(self, root: Path) -> dict[str, Any]:
        files = self._iter_doc_files(root)
        latest_mtime_ns = max((path.stat().st_mtime_ns for path in files), default=0)
        total_size = sum(path.stat().st_size for path in files)
        return {
            "schema_version": INDEX_SCHEMA_VERSION,
            "root": root.name,
            "file_count": len(files),
            "latest_mtime_ns": latest_mtime_ns,
            "total_size": total_size,
        }

    def _default_docs_source_root(self) -> Path | None:
        try:
            candidate = self.library_root.parent.parent / "docs" / "nova_school"
        except Exception:
            return None
        return candidate if candidate.exists() else None

    def _ensure_managed_pack(self, slug: str) -> None:
        if slug != "nova-school" or self.nova_product_docs is None:
            return
        self.nova_product_docs.ensure_built()

    @staticmethod
    def _status_for_slug(slug: str, installed: bool) -> str:
        if not installed:
            return "starter"
        if REFERENCE_PACKS[slug]["source_kind"] == "product":
            return "official-local"
        return "mirrored"

    def _index_is_stale(self, slug: str) -> bool:
        root = self._content_root(slug)
        index_path = self._index_path(slug)
        if root is None:
            return False
        if not index_path.exists():
            return True
        try:
            payload = json.loads(index_path.read_text(encoding="utf-8"))
        except Exception:
            return True
        stored_meta = payload.get("meta") or {}
        current_meta = self._pack_signature(root)
        return stored_meta != current_meta

    @staticmethod
    def _extract_document_data(path: Path, content: str) -> tuple[str, str, str]:
        suffix = path.suffix.lower()
        if suffix in {".html", ".htm"}:
            title_match = re.search(r"<title[^>]*>(.*?)</title>", content, flags=re.IGNORECASE | re.DOTALL)
            heading_match = re.search(r"<h1[^>]*>(.*?)</h1>", content, flags=re.IGNORECASE | re.DOTALL)
            raw_title = title_match.group(1) if title_match else heading_match.group(1) if heading_match else path.stem
            title = ReferenceLibraryService._collapse_ws(ReferenceLibraryService._strip_tags(raw_title)) or path.stem
            plain_text = ReferenceLibraryService._collapse_ws(ReferenceLibraryService._strip_tags(content))
            return title, plain_text, "html"
        if suffix == ".md":
            title = path.stem
            for line in content.splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            return title, ReferenceLibraryService._markdown_plain_text(content), "markdown"
        first_line = next((line.strip() for line in content.splitlines() if line.strip()), path.stem)
        return first_line, ReferenceLibraryService._collapse_ws(content), "text"

    @staticmethod
    def _strip_tags(value: str) -> str:
        text = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        return html.unescape(text)

    @staticmethod
    def _collapse_ws(value: str) -> str:
        return re.sub(r"\s+", " ", value or "").strip()

    @staticmethod
    def _markdown_plain_text(value: str) -> str:
        text = re.sub(r"```(?:[^\n]*)\n([\s\S]*?)```", r" \1 ", value)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*[-*]\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\|", " ", text)
        return ReferenceLibraryService._collapse_ws(text)

    @staticmethod
    def _snippet(text: str, terms: list[str]) -> str:
        plain = ReferenceLibraryService._collapse_ws(text)
        if not plain:
            return "Keine Vorschau verfuegbar."
        lowered = plain.lower()
        positions = [lowered.find(term) for term in terms if term in lowered]
        start = max(0, min(positions) - 90) if positions else 0
        end = min(len(plain), start + 220)
        prefix = "..." if start > 0 else ""
        suffix = "..." if end < len(plain) else ""
        return f"{prefix}{plain[start:end]}{suffix}"

    def _render_shell(
        self,
        *,
        selected_area: str,
        catalog: list[dict[str, Any]],
        documents: list[dict[str, Any]],
        active_doc: dict[str, Any] | None,
        query: str,
        results: list[dict[str, Any]],
        result_summary: str,
    ) -> str:
        selected_label = REFERENCE_PACKS[selected_area]["label"]
        selected_catalog = next((item for item in catalog if item["slug"] == selected_area), None) or {}
        selected_source = html.escape(str(selected_catalog.get("source_label") or REFERENCE_PACKS[selected_area]["source_label"]))
        selected_status = html.escape(str(selected_catalog.get("status") or "starter"))
        selected_count = int(selected_catalog.get("doc_count") or len(documents))
        doc_nav = "".join(
            (
                f'<a class="reference-nav-link {"active" if active_doc and item["doc_id"] == active_doc["doc_id"] else ""}" '
                f'href="{html.escape(self._reference_url(selected_area, str(item["doc_id"]), query), quote=True)}">{html.escape(str(item["title"]))}</a>'
            )
            for item in documents[:40]
        ) or '<p class="reference-muted">Noch keine Dokumente in diesem Bereich.</p>'
        area_cards = "".join(
            (
                f'<a class="reference-area-card {"active" if item["slug"] == selected_area else ""}" '
                f'href="{html.escape(self._reference_url(str(item["slug"]), "", query), quote=True)}">'
                f'<strong>{html.escape(str(item["label"]))}</strong>'
                f'<span>{html.escape(str(item["source_label"]))}</span>'
                f'<small>Status: {html.escape(str(item["status"]))} | Dokumente: {int(item["doc_count"])}</small>'
                "</a>"
            )
            for item in catalog
        )
        search_results = "".join(
            (
                f'<a class="reference-result" href="{html.escape(self._reference_url(str(item["area"]), str(item["doc_id"]), query), quote=True)}">'
                f'<strong>{html.escape(str(item["title"]))}</strong>'
                f'<span>{html.escape(str(item["area_label"]))}</span>'
                f'<small>{html.escape(str(item["snippet"]))}</small>'
                "</a>"
            )
            for item in results
        ) or ('<p class="reference-muted">Keine Treffer fuer diese Suche.</p>' if query.strip() else "")
        active_content = self._active_document_markup(selected_area, active_doc)
        install_path = html.escape(str(selected_catalog.get("install_path") or self._site_root(selected_area)))
        return f"""<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Offline Referenzbibliothek | Nova School</title>
    <link rel="stylesheet" href="/static/app.css" />
    <link rel="stylesheet" href="/static/reference.css" />
  </head>
  <body class="reference-body" data-reference-page="true">
    <div class="page-bg"></div>
    <div class="reference-shell" data-reference-shell>
      <header class="reference-hero">
        <div>
          <p class="eyebrow">Offline Referenzbibliothek</p>
          <h1>{html.escape(selected_label)}</h1>
          <p class="reference-lead">Originale oder primaere Dokumentation wird lokal auf dem Schulserver gespiegelt und ohne Webzugriff an die Clients ausgeliefert. Bis ein Bereich importiert ist, bleibt der vorhandene Schnellstart als Fallback verfuegbar.</p>
        </div>
        <div class="reference-actions">
          <button type="button" class="reference-button" data-reference-sidebar-toggle aria-expanded="true" aria-controls="reference-sidebar">Bereiche ausblenden</button>
          <button type="button" class="reference-button" data-reference-wide-toggle aria-pressed="false">Breiter Lesemodus</button>
          <a class="reference-button primary" href="/">Zur Nova-School-Oberflaeche</a>
        </div>
      </header>

      <section class="reference-card reference-toolbar">
        <div class="reference-toolbar-group">
          <span class="reference-chip">Quelle: {selected_source}</span>
          <span class="reference-chip">Status: {selected_status}</span>
          <span class="reference-chip">{selected_count} Dokumente</span>
        </div>
        <div class="reference-toolbar-group">
          <span class="reference-muted">{html.escape(result_summary)}</span>
        </div>
      </section>

      <section class="reference-grid" data-reference-layout>
        <aside class="reference-sidebar" id="reference-sidebar" data-reference-sidebar>
          <div class="reference-sidebar-rail">
            <section class="reference-card">
              <div class="reference-section-head">
                <h2>Bereiche</h2>
                <button type="button" class="reference-inline-button" data-reference-sidebar-toggle aria-expanded="true" aria-controls="reference-sidebar">Einklappen</button>
              </div>
              <div class="reference-area-list">
                {area_cards}
              </div>
            </section>

            <section class="reference-card">
              <h2>Dokumente</h2>
              <div class="reference-nav">
                {doc_nav}
              </div>
            </section>

            <section class="reference-card">
              <h2>Importpfad</h2>
              <p class="reference-muted">Lege fuer ein echtes Offline-Mirror die offiziellen oder kanonischen Dateien direkt in diesen Bereichsordner oder optional in den Unterordner <code>site</code>. Neue oder geaenderte Dateien werden automatisch neu indiziert:</p>
              <pre class="reference-path">{install_path}</pre>
            </section>
          </div>
        </aside>

        <main class="reference-main">
          <section class="reference-card">
            <form class="reference-search" method="GET" action="/reference">
              <input type="hidden" name="area" value="{html.escape(selected_area, quote=True)}" />
              <label>
                <span>Suche in {html.escape(selected_label)}</span>
                <input type="text" name="q" value="{html.escape(query)}" placeholder="API, loops, class, borrow, package.json, selector ..." />
              </label>
              <button type="submit" class="primary">Suchen</button>
            </form>
            {'<div class="reference-results">' + search_results + '</div>' if query.strip() else ''}
          </section>

          <section class="reference-card">
            {active_content}
          </section>
        </main>
      </section>
    </div>
    <script src="/static/reference.js"></script>
  </body>
</html>
"""

    def _active_document_markup(self, selected_area: str, active_doc: dict[str, Any] | None) -> str:
        if active_doc is None:
            return "<p class=\"reference-muted\">Noch kein Dokument verfuegbar.</p>"
        raw_title = str(active_doc["title"])
        title = html.escape(raw_title)
        status = html.escape(str(active_doc.get("status") or "starter"))
        if active_doc.get("viewer") == "iframe":
            asset_url = self._asset_url(selected_area, str(active_doc.get("rel_path") or ""))
            return (
                f"<div class=\"reference-doc-head\"><h2>{title}</h2><p class=\"reference-muted\">Status: {status} | Quelle wird lokal gespiegelt ausgeliefert.</p></div>"
                f"<iframe class=\"reference-frame\" src=\"{html.escape(asset_url, quote=True)}\" loading=\"lazy\"></iframe>"
            )
        content = str(active_doc.get("content") or "")
        if not content:
            content = str(active_doc.get("render_content") or "")
        if not content and active_doc.get("rel_path"):
            path = self.resolve_asset(selected_area, str(active_doc["rel_path"]))
            content = path.read_text(encoding="utf-8", errors="ignore")
            if selected_area == "cpp" and path.suffix.lower() == ".md":
                content = self._normalize_cpp_markdown(str(active_doc["rel_path"]), content)
        if active_doc.get("content_type") == "markdown":
            content = self._strip_duplicate_first_heading(content, raw_title)
            rendered = self._markdown_to_html(content)
        elif active_doc.get("content_type") == "text":
            rendered = f"<pre class=\"reference-pre\">{html.escape(content)}</pre>"
        else:
            rendered = f"<pre class=\"reference-pre\">{html.escape(content)}</pre>"
        fallback_note = (
            "<p class=\"reference-notice\">Dieser Bereich nutzt aktuell den lokalen Schnellstart-Fallback. Sobald ein offizielles Offline-Mirror im Importpfad liegt, wird hier automatisch die gespiegelte Referenz angezeigt.</p>"
            if active_doc.get("status") == "starter"
            else ""
        )
        return f"<div class=\"reference-doc-head\"><h2>{title}</h2><p class=\"reference-muted\">Status: {status}</p></div>{fallback_note}<article class=\"reference-article\">{rendered}</article>"

    @staticmethod
    def _reference_url(area: str, doc_id: str, query: str) -> str:
        parts = [f"area={quote(area)}"]
        if doc_id:
            parts.append(f"doc={quote(doc_id)}")
        if query.strip():
            parts.append(f"q={quote(query.strip())}")
        return "/reference?" + "&".join(parts)

    @staticmethod
    def _asset_url(area: str, rel_path: str) -> str:
        encoded = "/".join(quote(part) for part in rel_path.split("/") if part)
        return f"/reference/assets/{quote(area)}/{encoded}"

    def _markdown_to_html(self, source: str) -> str:
        lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        blocks: list[str] = []
        index = 0
        while index < len(lines):
            line = lines[index]
            stripped = line.strip()
            if not stripped:
                index += 1
                continue
            if stripped.startswith("```"):
                language = stripped[3:].strip()
                code_lines: list[str] = []
                index += 1
                while index < len(lines) and not lines[index].strip().startswith("```"):
                    code_lines.append(lines[index])
                    index += 1
                if index < len(lines):
                    index += 1
                language_attr = f' data-language="{html.escape(language)}"' if language else ""
                blocks.append(
                    f"<pre class=\"reference-pre\"><code{language_attr}>{html.escape(chr(10).join(code_lines)).strip()}</code></pre>"
                )
                continue
            if self._is_table_header(lines, index):
                table_html, index = self._render_table(lines, index)
                blocks.append(table_html)
                continue
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", stripped)
            if heading_match:
                level = len(heading_match.group(1))
                blocks.append(f"<h{level}>{self._render_inline(heading_match.group(2).strip())}</h{level}>")
                index += 1
                continue
            if re.match(r"^\s*-\s+.+$", line):
                items: list[str] = []
                while index < len(lines) and re.match(r"^\s*-\s+.+$", lines[index]):
                    items.append(re.sub(r"^\s*-\s+", "", lines[index]).strip())
                    index += 1
                blocks.append("<ul>" + "".join(f"<li>{self._render_inline(item)}</li>" for item in items) + "</ul>")
                continue
            if re.match(r"^\s*\d+\.\s+.+$", line):
                items = []
                while index < len(lines) and re.match(r"^\s*\d+\.\s+.+$", lines[index]):
                    items.append(re.sub(r"^\s*\d+\.\s+", "", lines[index]).strip())
                    index += 1
                blocks.append("<ol>" + "".join(f"<li>{self._render_inline(item)}</li>" for item in items) + "</ol>")
                continue
            paragraph_lines: list[str] = []
            while (
                index < len(lines)
                and lines[index].strip()
                and not lines[index].strip().startswith("```")
                and not self._is_table_header(lines, index)
                and not re.match(r"^(#{1,6})\s+.+$", lines[index].strip())
                and not re.match(r"^\s*-\s+.+$", lines[index])
                and not re.match(r"^\s*\d+\.\s+.+$", lines[index])
            ):
                paragraph_lines.append(lines[index].strip())
                index += 1
            blocks.append(f"<p>{self._render_inline(' '.join(paragraph_lines))}</p>")
        return "\n".join(blocks)

    @staticmethod
    def _is_table_header(lines: list[str], index: int) -> bool:
        if index + 1 >= len(lines):
            return False
        header = lines[index].strip()
        separator = lines[index + 1].strip()
        return header.startswith("|") and header.endswith("|") and re.match(r"^\|(?:\s*:?-{3,}:?\s*\|)+\s*$", separator) is not None

    def _render_table(self, lines: list[str], index: int) -> tuple[str, int]:
        header_cells = self._parse_table_row(lines[index])
        index += 2
        body_rows: list[list[str]] = []
        while index < len(lines):
            row = lines[index].strip()
            if not row.startswith("|") or not row.endswith("|"):
                break
            body_rows.append(self._parse_table_row(lines[index]))
            index += 1
        header_html = "".join(f"<th>{self._render_inline(cell)}</th>" for cell in header_cells)
        body_html = "".join(
            "<tr>" + "".join(f"<td>{self._render_inline(cell)}</td>" for cell in row) + "</tr>"
            for row in body_rows
        )
        return (
            f'<div class="reference-table-wrap"><table class="reference-table"><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table></div>',
            index,
        )

    @staticmethod
    def _parse_table_row(row: str) -> list[str]:
        return [cell.strip() for cell in row.strip().strip("|").split("|")]

    @staticmethod
    def _render_plain_inline(text: str) -> str:
        escaped = html.escape(text)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
        return escaped

    def _render_inline(self, text: str) -> str:
        pattern = re.compile(r"(`[^`]+`|\[[^\]]+\]\([^)]+\))")
        cursor = 0
        fragments: list[str] = []
        for match in pattern.finditer(text):
            if match.start() > cursor:
                fragments.append(self._render_plain_inline(text[cursor:match.start()]))
            token = match.group(0)
            if token.startswith("`"):
                fragments.append(f"<code>{html.escape(token[1:-1])}</code>")
            else:
                link_match = re.match(r"^\[(?P<label>[^\]]+)\]\((?P<target>[^)]+)\)$", token)
                if link_match:
                    label = html.escape(link_match.group("label"))
                    target = html.escape(link_match.group("target"), quote=True)
                    fragments.append(f'<a href="{target}">{label}</a>')
                else:
                    fragments.append(html.escape(token))
            cursor = match.end()
        if cursor < len(text):
            fragments.append(self._render_plain_inline(text[cursor:]))
        return "".join(fragments)

    @staticmethod
    def _strip_duplicate_first_heading(source: str, title: str) -> str:
        normalized_title = (title or "").strip().casefold()
        lines = source.splitlines()
        for index, line in enumerate(lines):
            stripped = line.strip()
            if not stripped:
                continue
            heading_match = re.match(r"^#\s+(.+)$", stripped)
            if heading_match and heading_match.group(1).strip().casefold() == normalized_title:
                remainder = lines[index + 1 :]
                while remainder and not remainder[0].strip():
                    remainder = remainder[1:]
                return "\n".join(remainder)
            break
        return source

    def _normalize_cpp_markdown(self, rel_path: str, source: str) -> str:
        text = source.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\[\s*edit\s*\]", "[edit]", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        if rel_path == "index.md":
            return text

        parts = [part.strip() for part in text.split("[edit]")]
        title = self._cpp_primary_title(rel_path, parts)
        blocks: list[str] = [f"# {title}"]

        intro = parts[2].strip() if len(parts) >= 3 else ""
        intro_blocks = self._cpp_intro_blocks(intro)
        if intro_blocks:
            blocks.extend(intro_blocks)

        for raw_section in parts[3:]:
            heading, body = self._split_cpp_section_heading(raw_section)
            if not heading and not body:
                continue
            if heading:
                blocks.append(f"### {heading}")
            if body:
                blocks.append(body)

        cleaned = "\n\n".join(block for block in blocks if block.strip())
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
        return cleaned + "\n"

    def _cpp_primary_title(self, rel_path: str, parts: list[str]) -> str:
        fallback = CPP_PAGE_TITLE_FALLBACKS.get(rel_path)
        if fallback:
            return fallback
        if len(parts) >= 2:
            candidate = self._collapse_ws(parts[1])
            candidate = re.sub(r"\s+", " ", candidate).strip()
            match = re.match(r"^(C\+\+\s+language|[A-Z][A-Za-z0-9+ /:-]+?library)\b", candidate)
            if match:
                return match.group(1).strip()
        return Path(rel_path).stem.replace("_", " ").strip().title()

    def _cpp_intro_blocks(self, intro: str) -> list[str]:
        text = intro.strip()
        if not text:
            return []
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = self._cleanup_cpp_block(text)
        if not text:
            return []
        contents_match = re.search(r"(##\s+Contents[\s\S]*)", text, flags=re.IGNORECASE)
        if contents_match:
            before = text[: contents_match.start()].strip()
            contents = contents_match.group(1).strip()
            contents = self._cleanup_cpp_block(contents)
            blocks: list[str] = []
            if before:
                blocks.append(before)
            if contents:
                blocks.append(contents)
            return blocks
        return [text]

    def _split_cpp_section_heading(self, section: str) -> tuple[str, str]:
        text = self._collapse_ws(section)
        if not text:
            return "", ""

        repeated_index = self._find_repeated_prefix_index(text)
        starter_positions = [
            text.find(marker)
            for marker in (
                " The ",
                " In ",
                " C++ ",
                " Defined ",
                " Most ",
                " Many ",
                " Several ",
                " Some ",
                " There ",
                " This ",
                " These ",
                " When ",
                " All ",
                " A ",
                " An ",
            )
        ]
        starter_positions = [position for position in starter_positions if 0 < position < 140]

        split_at = min([position for position in [repeated_index, *starter_positions] if position > 0], default=-1)
        if split_at > 0:
            heading = text[:split_at].strip(" -:")
            body = self._cleanup_cpp_block(text[split_at:])
            return heading, body

        words = text.split()
        if not words:
            return "", ""

        heading_words = [words[0]]
        index = 1
        while index < len(words) and (
            words[index].startswith("(")
            or words[index].endswith(")")
            or words[index].startswith("<")
            or words[index].endswith(">")
            or words[index].startswith("std::")
            or words[index].startswith("pmr::")
        ):
            heading_words.append(words[index])
            index += 1
        heading = " ".join(heading_words).strip(" -:")
        body = self._cleanup_cpp_block(" ".join(words[index:]))

        if heading.lower() in {"see", "defined", "feature", "member", "non-member"} and body:
            more = body.split(" ", 1)
            heading = f"{heading} {more[0]}".strip()
            body = more[1].strip() if len(more) > 1 else ""
        return heading, body

    @staticmethod
    def _find_repeated_prefix_index(text: str) -> int:
        words = text.split()
        max_words = min(4, len(words))
        for count in range(max_words, 0, -1):
            prefix = " ".join(words[:count]).strip()
            if len(prefix) < 6:
                continue
            repeated = text.find(f" {prefix} ", len(prefix) + 1)
            if 0 < repeated < 140:
                return repeated + 1
        return -1

    @staticmethod
    def _cleanup_cpp_block(text: str) -> str:
        cleaned = text.strip()
        cleaned = re.sub(r"(?:^|\n)#{2,6}\s*$", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\s+#{2,6}\s*$", "", cleaned)
        cleaned = re.sub(r":\s+-\s+", ":\n- ", cleaned)
        while True:
            updated = re.sub(r"(?m)(^-\s[^\n]+?)\s+-\s+(?=[A-Za-z])", r"\1\n- ", cleaned)
            if updated == cleaned:
                break
            cleaned = updated
        return cleaned.strip()

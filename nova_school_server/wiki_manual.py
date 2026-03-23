from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote


SCOPE_CONFIG: dict[str, dict[str, str]] = {
    "teacher-admin": {
        "folder": "Lehrer_Admin",
        "label": "Lehrkräfte und Administration",
        "audience": "Didaktik, Moderation, Rechteverwaltung, Sicherheit und Systembetrieb",
    },
    "student-user": {
        "folder": "Schüler_User",
        "label": "Schüler und Nutzer",
        "audience": "Arbeitsalltag im Editor, Notebooks, KI-Hilfe, Chat und Abgabe",
    },
}


class WikiManualService:
    def __init__(self, wiki_root: Path) -> None:
        self.wiki_root = wiki_root

    def allowed_scopes(self, session: Any) -> list[str]:
        return ["teacher-admin", "student-user"] if bool(getattr(session, "is_teacher", False)) else ["student-user"]

    def default_scope(self, session: Any) -> str:
        return "teacher-admin" if bool(getattr(session, "is_teacher", False)) else "student-user"

    def render_page(self, session: Any, requested_scope: str | None = None, requested_page: str | None = None) -> str:
        scope = self._resolve_scope(session, requested_scope)
        documents = self.documents(scope)
        if not documents:
            raise FileNotFoundError(f"Kein Handbuch im Bereich {scope} gefunden.")
        requested_slug = (requested_page or "").strip().casefold()
        document = next((item for item in documents if str(item["slug"]).casefold() == requested_slug), documents[0])
        content = document["path"].read_text(encoding="utf-8")
        toc = self._collect_toc(content)
        return self._render_shell(
            session=session,
            scope=scope,
            document=document,
            documents=documents,
            allowed_scopes=self.allowed_scopes(session),
            toc=toc,
            article_html=self._markdown_to_html(content, scope=scope),
        )

    def documents(self, scope: str) -> list[dict[str, Any]]:
        folder = self._scope_folder(scope)
        if not folder.exists():
            return []
        docs: list[dict[str, Any]] = []
        for path in sorted(folder.glob("*.md"), key=self._document_sort_key):
            content = path.read_text(encoding="utf-8")
            docs.append(
                {
                    "slug": path.stem,
                    "filename": path.name,
                    "title": self._extract_title(content, path),
                    "path": path,
                }
            )
        return docs

    def _resolve_scope(self, session: Any, requested_scope: str | None) -> str:
        allowed = self.allowed_scopes(session)
        if requested_scope in allowed:
            return str(requested_scope)
        default_scope = self.default_scope(session)
        return default_scope if default_scope in allowed else allowed[0]

    def _scope_folder(self, scope: str) -> Path:
        config = SCOPE_CONFIG.get(scope)
        if config is None:
            raise FileNotFoundError(f"Unbekannter Handbuchbereich: {scope}")
        return self.wiki_root / config["folder"]

    @staticmethod
    def _document_sort_key(path: Path) -> tuple[int, str]:
        if path.name.lower() == "readme.md":
            return (0, path.name.lower())
        return (1, path.name.lower())

    @staticmethod
    def _extract_title(content: str, path: Path) -> str:
        for line in content.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return " ".join(part for part in path.stem.replace("_", " ").split() if part).strip() or path.stem

    def _collect_toc(self, content: str) -> list[dict[str, str | int]]:
        toc: list[dict[str, str | int]] = []
        seen: dict[str, int] = {}
        for raw_line in content.splitlines():
            match = re.match(r"^(#{2,3})\s+(.+?)\s*$", raw_line.strip())
            if not match:
                continue
            level = len(match.group(1))
            title = match.group(2).strip()
            toc.append({"level": level, "title": title, "anchor": self._anchor_id(title, seen)})
        return toc

    def _markdown_to_html(self, source: str, *, scope: str) -> str:
        lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        blocks: list[str] = []
        index = 0
        heading_ids: dict[str, int] = {}
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
                    f'<pre class="manual-code"><code{language_attr}>{html.escape(chr(10).join(code_lines)).strip()}</code></pre>'
                )
                continue

            if self._is_table_header(lines, index):
                table_html, index = self._render_table(lines, index, scope)
                blocks.append(table_html)
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.+?)\s*$", stripped)
            if heading_match:
                level = len(heading_match.group(1))
                title = heading_match.group(2).strip()
                anchor = self._anchor_id(title, heading_ids)
                blocks.append(f'<h{level} id="{anchor}">{self._render_inline(title, scope=scope)}</h{level}>')
                index += 1
                continue

            if re.match(r"^\s*-\s+.+$", line):
                items: list[str] = []
                while index < len(lines) and re.match(r"^\s*-\s+.+$", lines[index]):
                    items.append(re.sub(r"^\s*-\s+", "", lines[index]).strip())
                    index += 1
                blocks.append("<ul>" + "".join(f"<li>{self._render_inline(item, scope=scope)}</li>" for item in items) + "</ul>")
                continue

            if re.match(r"^\s*\d+\.\s+.+$", line):
                items = []
                while index < len(lines) and re.match(r"^\s*\d+\.\s+.+$", lines[index]):
                    items.append(re.sub(r"^\s*\d+\.\s+", "", lines[index]).strip())
                    index += 1
                blocks.append("<ol>" + "".join(f"<li>{self._render_inline(item, scope=scope)}</li>" for item in items) + "</ol>")
                continue

            paragraph_lines: list[str] = []
            while index < len(lines):
                current = lines[index]
                current_stripped = current.strip()
                if not current_stripped:
                    break
                if current_stripped.startswith("```"):
                    break
                if self._is_table_header(lines, index):
                    break
                if re.match(r"^(#{1,6})\s+.+$", current_stripped):
                    break
                if re.match(r"^\s*-\s+.+$", current):
                    break
                if re.match(r"^\s*\d+\.\s+.+$", current):
                    break
                paragraph_lines.append(current_stripped)
                index += 1
            paragraph = " ".join(paragraph_lines).strip()
            if paragraph:
                blocks.append(f"<p>{self._render_inline(paragraph, scope=scope)}</p>")
            else:
                index += 1

        return "\n".join(blocks)

    @staticmethod
    def _is_table_header(lines: list[str], index: int) -> bool:
        if index + 1 >= len(lines):
            return False
        header = lines[index].strip()
        separator = lines[index + 1].strip()
        return header.startswith("|") and header.endswith("|") and re.match(r"^\|(?:\s*:?-{3,}:?\s*\|)+\s*$", separator) is not None

    def _render_table(self, lines: list[str], index: int, scope: str) -> tuple[str, int]:
        header_cells = self._parse_table_row(lines[index])
        index += 2
        body_rows: list[list[str]] = []
        while index < len(lines):
            row = lines[index].strip()
            if not row.startswith("|") or not row.endswith("|"):
                break
            body_rows.append(self._parse_table_row(lines[index]))
            index += 1
        header_html = "".join(f"<th>{self._render_inline(cell, scope=scope)}</th>" for cell in header_cells)
        body_html = "".join(
            "<tr>" + "".join(f"<td>{self._render_inline(cell, scope=scope)}</td>" for cell in row) + "</tr>"
            for row in body_rows
        )
        return f'<div class="manual-table-wrap"><table class="manual-table"><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table></div>', index

    @staticmethod
    def _parse_table_row(row: str) -> list[str]:
        return [cell.strip() for cell in row.strip().strip("|").split("|")]

    def _render_inline(self, text: str, *, scope: str) -> str:
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
                    target = self._resolve_link(scope, link_match.group("target").strip())
                    fragments.append(f'<a href="{html.escape(target, quote=True)}">{label}</a>')
                else:
                    fragments.append(html.escape(token))
            cursor = match.end()
        if cursor < len(text):
            fragments.append(self._render_plain_inline(text[cursor:]))
        return "".join(fragments)

    @staticmethod
    def _render_plain_inline(text: str) -> str:
        escaped = html.escape(text)
        escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
        escaped = re.sub(r"\*(.+?)\*", r"<em>\1</em>", escaped)
        return escaped

    def _resolve_link(self, current_scope: str, target: str) -> str:
        if target.startswith(("http://", "https://", "mailto:", "#", "/")):
            return html.escape(target, quote=True)
        normalized = target.replace("\\", "/")
        target_scope = current_scope
        for scope, payload in SCOPE_CONFIG.items():
            if payload["folder"] in normalized:
                target_scope = scope
                break
        if normalized.endswith(".md"):
            slug = Path(normalized).stem
            return f"/manual?scope={quote(target_scope)}&page={quote(slug)}"
        return html.escape(normalized, quote=True)

    @staticmethod
    def _anchor_id(title: str, seen: dict[str, int]) -> str:
        slug = title.lower()
        replacements = {
            "ä": "ae",
            "ö": "oe",
            "ü": "ue",
            "ß": "ss",
        }
        for needle, replacement in replacements.items():
            slug = slug.replace(needle, replacement)
        slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-") or "abschnitt"
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        return slug if count == 0 else f"{slug}-{count + 1}"

    def _render_shell(
        self,
        *,
        session: Any,
        scope: str,
        document: dict[str, Any],
        documents: list[dict[str, Any]],
        allowed_scopes: list[str],
        toc: list[dict[str, str | int]],
        article_html: str,
    ) -> str:
        current_scope = SCOPE_CONFIG[scope]
        title = html.escape(str(document["title"]))
        display_name = html.escape(str(getattr(session, "user", {}).get("display_name", getattr(session, "username", "Benutzer"))))
        role = html.escape(str(getattr(session, "role", "student")))
        scope_switch = "".join(
            (
                f'<a class="manual-scope {"active" if item == scope else ""}" href="{html.escape(f"/manual?scope={quote(item)}", quote=True)}">'
                f'{html.escape(SCOPE_CONFIG[item]["label"])}</a>'
            )
            for item in allowed_scopes
        )
        nav_links = "".join(
            (
                f'<a class="manual-nav-link {"active" if item["slug"] == document["slug"] else ""}" '
                f'href="{html.escape(f"/manual?scope={quote(scope)}&page={quote(str(item["slug"]))}", quote=True)}">{html.escape(str(item["title"]))}</a>'
            )
            for item in documents
        )
        toc_links = "".join(
            (
                f'<a class="manual-toc-link level-{int(item["level"])}" href="#{html.escape(str(item["anchor"]))}">'
                f'{html.escape(str(item["title"]))}</a>'
            )
            for item in toc
        ) or '<p class="manual-muted">Keine Unterabschnitte in diesem Dokument.</p>'
        return f"""<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{title} | Nova School Handbuch</title>
    <link rel="stylesheet" href="/static/app.css" />
    <link rel="stylesheet" href="/static/manual.css" />
  </head>
  <body class="manual-body">
    <div class="page-bg"></div>
    <div class="manual-shell">
      <header class="manual-hero">
        <div>
          <p class="eyebrow">Nova School Handbuch</p>
          <h1>{title}</h1>
          <p class="manual-lead">{html.escape(current_scope["audience"])}</p>
        </div>
        <div class="manual-hero-meta">
          <p><strong>Angemeldet als:</strong> {display_name}</p>
          <p><strong>Rolle:</strong> {role}</p>
          <p><strong>Bereich:</strong> {html.escape(current_scope["label"])}</p>
        </div>
        <div class="manual-actions">
          <a class="manual-button primary" href="/">Zur Nova-School-Oberfläche</a>
        </div>
      </header>

      <section class="manual-switcher">
        {scope_switch}
      </section>

      <div class="manual-layout">
        <aside class="manual-sidebar">
          <section class="manual-card">
            <h2>Dokumente</h2>
            <nav class="manual-nav">
              {nav_links}
            </nav>
          </section>
          <section class="manual-card">
            <h2>Auf dieser Seite</h2>
            <nav class="manual-toc">
              {toc_links}
            </nav>
          </section>
        </aside>

        <main class="manual-main">
          <article class="manual-article">
            {article_html}
          </article>
        </main>
      </div>
    </div>
  </body>
</html>
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlsplit


ATTR_RE = re.compile(
    r"(?P<attr>\b(?:href|src|poster|action)=)(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
    flags=re.IGNORECASE | re.DOTALL,
)
SRCSET_RE = re.compile(
    r"(?P<attr>\bsrcset=)(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
    flags=re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True, slots=True)
class MirrorSource:
    label: str
    url: str


@dataclass(frozen=True, slots=True)
class MirrorPack:
    slug: str
    title: str
    intro: str
    sources: tuple[MirrorSource, ...]
    domains: tuple[str, ...]
    accept_regex: str
    level: int | None = None


MIRROR_PACKS: dict[str, MirrorPack] = {
    "javascript": MirrorPack(
        slug="javascript",
        title="JavaScript Offline Mirror",
        intro="MDN JavaScript Guide und Referenz werden lokal gespiegelt und komplett ohne externen Webzugriff ausgeliefert.",
        sources=(
            MirrorSource("MDN JavaScript", "https://developer.mozilla.org/en-US/docs/Web/JavaScript"),
        ),
        domains=("developer.mozilla.org",),
        accept_regex=r"^https?://developer\.mozilla\.org(/en-US/docs/Web/JavaScript(/|$)|/static/|/files/)",
        level=4,
    ),
    "java": MirrorPack(
        slug="java",
        title="Java Offline Mirror",
        intro="Offizielle Java-Lerninhalte von dev.java und die Java-21-API-Dokumentation von Oracle werden lokal gespiegelt.",
        sources=(
            MirrorSource("Dev.java Learn", "https://dev.java/learn/"),
            MirrorSource("Java 21 API", "https://docs.oracle.com/en/java/javase/21/docs/api/"),
        ),
        domains=("dev.java", "docs.oracle.com"),
        accept_regex=(
            r"^https?://(dev\.java(/learn(/|$)|/assets/)"
            r"|docs\.oracle\.com(/en/java/javase/21/docs/api(/|$)|/en/dcommon/(js|css|images)(/|$)))"
        ),
        level=4,
    ),
    "rust": MirrorPack(
        slug="rust",
        title="Rust Offline Mirror",
        intro="The Rust Programming Language, The Rust Reference und die Standardbibliothek werden lokal gespiegelt.",
        sources=(
            MirrorSource("The Rust Programming Language", "https://doc.rust-lang.org/book/"),
            MirrorSource("The Rust Reference", "https://doc.rust-lang.org/reference/"),
            MirrorSource("Rust Standard Library", "https://doc.rust-lang.org/std/"),
        ),
        domains=("doc.rust-lang.org",),
        accept_regex=(
            r"^https?://doc\.rust-lang\.org(/(book|reference|std)(/|$)|/static\.files/|/crates[^/]+\.js$)"
        ),
        level=4,
    ),
    "html-css": MirrorPack(
        slug="html-css",
        title="HTML und CSS Offline Mirror",
        intro="MDN HTML- und CSS-Referenzen werden lokal gespiegelt und fuer den Unterricht offline ausgeliefert.",
        sources=(
            MirrorSource("MDN HTML", "https://developer.mozilla.org/en-US/docs/Web/HTML"),
            MirrorSource("MDN CSS", "https://developer.mozilla.org/en-US/docs/Web/CSS"),
        ),
        domains=("developer.mozilla.org",),
        accept_regex=r"^https?://developer\.mozilla\.org(/en-US/docs/Web/(HTML|CSS)(/|$)|/static/|/files/)",
        level=4,
    ),
    "node-npm": MirrorPack(
        slug="node-npm",
        title="Node.js und npm Offline Mirror",
        intro="Offizielle Node.js-API-Dokumentation und npm-CLI-Dokumentation werden lokal gespiegelt.",
        sources=(
            MirrorSource("Node.js API", "https://nodejs.org/docs/latest/api/"),
            MirrorSource("npm CLI", "https://docs.npmjs.com/cli/v11/"),
            MirrorSource("npm package.json", "https://docs.npmjs.com/cli/v11/configuring-npm/package-json/"),
        ),
        domains=("nodejs.org", "fonts.googleapis.com", "fonts.gstatic.com", "docs.npmjs.com"),
        accept_regex=(
            r"^https?://(nodejs\.org(/docs/latest/api(/|$)|/favicon\.ico$)"
            r"|fonts\.googleapis\.com/.*"
            r"|fonts\.gstatic\.com/.*"
            r"|docs\.npmjs\.com(/cli/v11(/|$)|/icons(/|$)|/manifest\.webmanifest$|/styles[^/]+\.css$|/favicon[^/]*$))"
        ),
        level=4,
    ),
    "web-frontend": MirrorPack(
        slug="web-frontend",
        title="Web Frontend Offline Mirror",
        intro="MDN Learn Web Development sowie zentrale Browser-API-Guides werden lokal fuer den Unterricht gespiegelt.",
        sources=(
            MirrorSource("Learn Web Development", "https://developer.mozilla.org/en-US/docs/Learn_web_development"),
            MirrorSource("Fetch API Guide", "https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch"),
            MirrorSource("HTML DOM API", "https://developer.mozilla.org/en-US/docs/Web/API/HTML_DOM_API"),
            MirrorSource("Service Worker API", "https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API"),
            MirrorSource("Using Web Workers", "https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API/Using_web_workers"),
        ),
        domains=("developer.mozilla.org",),
        accept_regex=(
            r"^https?://developer\.mozilla\.org("
            r"/en-US/docs/Learn_web_development(/|$)"
            r"|/en-US/docs/Web/API/(Fetch_API(/|$)|HTML_DOM_API(/|$)|Service_Worker_API(/|$)|Web_Workers_API(/|$))"
            r"|/static/|/files/)"
        ),
        level=4,
    ),
}


class ReferenceWebMirrorBuilder:
    def __init__(
        self,
        *,
        pack: MirrorPack,
        output_root: Path,
        clean: bool = False,
        wget_path: str | None = None,
    ) -> None:
        self.pack = pack
        self.output_root = output_root
        self.site_root = self.output_root / "site"
        self.clean = clean
        self.wget_path = wget_path or shutil.which("wget") or shutil.which("wget.exe") or "wget"
        self.manifest_path = self.output_root / "web_mirror_manifest.json"

    def build(self) -> dict[str, object]:
        self.output_root.mkdir(parents=True, exist_ok=True)
        if self.clean and self.site_root.exists():
            shutil.rmtree(self.site_root)
        self.site_root.mkdir(parents=True, exist_ok=True)

        started_at = time.time()
        runs: list[dict[str, object]] = []
        for source in self.pack.sources:
            command = self._build_wget_command(source)
            subprocess.run(command, cwd=self.site_root, check=True)
            runs.append({"label": source.label, "url": source.url, "command": command})

        self._rewrite_mirror_html()
        landing_entries = self._write_landing_page()
        manifest = {
            "pack": self.pack.slug,
            "title": self.pack.title,
            "domains": list(self.pack.domains),
            "accept_regex": self.pack.accept_regex,
            "level": self.pack.level,
            "sources": runs,
            "landing_entries": landing_entries,
            "generated_at_epoch": int(time.time()),
            "duration_seconds": round(time.time() - started_at, 2),
        }
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest

    def finalize_existing_site(self) -> dict[str, object]:
        if not self.site_root.exists():
            raise FileNotFoundError(f"Kein Mirror unter {self.site_root} vorhanden.")
        started_at = time.time()
        self._rewrite_mirror_html()
        landing_entries = self._write_landing_page()
        manifest = {
            "pack": self.pack.slug,
            "title": self.pack.title,
            "domains": list(self.pack.domains),
            "accept_regex": self.pack.accept_regex,
            "level": self.pack.level,
            "sources": [{"label": source.label, "url": source.url} for source in self.pack.sources],
            "landing_entries": landing_entries,
            "download_skipped": True,
            "generated_at_epoch": int(time.time()),
            "duration_seconds": round(time.time() - started_at, 2),
        }
        self.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest

    def _build_wget_command(self, source: MirrorSource) -> list[str]:
        command = [
            self.wget_path,
            "--mirror",
            "--convert-links",
            "--adjust-extension",
            "--page-requisites",
            "--span-hosts",
            "--no-parent",
            "--restrict-file-names=windows",
            "--user-agent=NovaSchoolServer/1.0 (+offline reference import)",
            f"--domains={','.join(self.pack.domains)}",
            f"--accept-regex={self.pack.accept_regex}",
            f"--directory-prefix={self.site_root}",
        ]
        if self.pack.level is not None:
            command.append(f"--level={self.pack.level}")
        command.append(source.url)
        return command

    def _rewrite_mirror_html(self) -> None:
        for html_path in sorted(self.site_root.rglob("*.html")):
            content = html_path.read_text(encoding="utf-8", errors="ignore")
            rewritten = ATTR_RE.sub(lambda match: self._rewrite_attr(html_path, match), content)
            rewritten = SRCSET_RE.sub(lambda match: self._rewrite_srcset(html_path, match), rewritten)
            html_path.write_text(rewritten, encoding="utf-8")

    def _rewrite_attr(self, current_path: Path, match: re.Match[str]) -> str:
        attr = match.group("attr")
        quote_char = match.group("quote")
        raw_value = html.unescape(match.group("value"))
        rewritten = self._rewrite_url(current_path, raw_value)
        return f"{attr}{quote_char}{html.escape(rewritten, quote=True)}{quote_char}"

    def _rewrite_srcset(self, current_path: Path, match: re.Match[str]) -> str:
        attr = match.group("attr")
        quote_char = match.group("quote")
        items: list[str] = []
        for raw_item in match.group("value").split(","):
            parts = raw_item.strip().split()
            if not parts:
                continue
            rewritten = self._rewrite_url(current_path, html.unescape(parts[0]))
            if len(parts) > 1:
                items.append(f"{rewritten} {' '.join(parts[1:])}")
            else:
                items.append(rewritten)
        return f"{attr}{quote_char}{html.escape(', '.join(items), quote=True)}{quote_char}"

    def _rewrite_url(self, current_path: Path, raw_value: str) -> str:
        value = (raw_value or "").strip()
        if not value or value.startswith(("#", "javascript:", "mailto:", "tel:", "data:")):
            return value
        if not self._is_absolute_or_root_relative(value):
            return value
        target = self.resolve_local_target(value)
        if target is None:
            return "#"
        return self._relative_href(current_path, target)

    @staticmethod
    def _is_absolute_or_root_relative(value: str) -> bool:
        return value.startswith("/") or value.startswith("http://") or value.startswith("https://")

    def resolve_local_target(self, raw_value: str) -> Path | None:
        parsed = urlsplit(raw_value)
        if parsed.scheme and parsed.netloc:
            if parsed.netloc not in self.pack.domains:
                return None
            host = parsed.netloc
            path = parsed.path or "/"
        else:
            host = self.pack.domains[0]
            path = parsed.path or "/"

        candidate_root = self.site_root / host
        clean_path = path.lstrip("/")
        if not clean_path:
            candidates = [candidate_root / "index.html"]
        else:
            base = candidate_root / clean_path
            suffix = Path(clean_path).suffix.lower()
            candidates = [base]
            if suffix in {".html", ".htm", ".css", ".js", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf"}:
                pass
            else:
                candidates.append(base.with_suffix(".html"))
                candidates.append(base / "index.html")

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    @staticmethod
    def _relative_href(current_path: Path, target_path: Path) -> str:
        return Path(shutil.os.path.relpath(target_path, current_path.parent)).as_posix()

    def _write_landing_page(self) -> list[dict[str, str]]:
        entries: list[dict[str, str]] = []
        for source in self.pack.sources:
            target = self.resolve_local_target(source.url)
            if target is None:
                continue
            entries.append(
                {
                    "label": source.label,
                    "url": source.url,
                    "href": Path(shutil.os.path.relpath(target, self.site_root)).as_posix(),
                }
            )

        list_markup = "".join(
            f'<li><a href="{html.escape(item["href"], quote=True)}">{html.escape(item["label"])}</a>'
            f'<small>{html.escape(item["url"])}</small></li>'
            for item in entries
        )
        landing_html = f"""<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(self.pack.title)}</title>
    <style>
      body {{ font-family: Georgia, "Times New Roman", serif; margin: 0; background: #fcfaf5; color: #182126; }}
      main {{ max-width: 1040px; margin: 0 auto; padding: 2.4rem 1.4rem 4rem; }}
      .note {{ background: #e6f1ee; color: #0a4d49; border-radius: 20px; padding: 1rem 1.2rem; }}
      ul {{ list-style: none; padding: 0; display: grid; gap: 1rem; }}
      li {{ background: rgba(255,255,255,0.88); border: 1px solid rgba(24,33,38,0.08); border-radius: 18px; padding: 1rem 1.1rem; box-shadow: 0 18px 40px rgba(24,33,38,0.08); }}
      li a {{ font-size: 1.1rem; font-weight: 700; color: #0c5b57; text-decoration: none; }}
      li small {{ display: block; margin-top: 0.45rem; color: #56656c; word-break: break-all; }}
    </style>
  </head>
  <body>
    <main>
      <h1>{html.escape(self.pack.title)}</h1>
      <p class="note">{html.escape(self.pack.intro)}</p>
      <ul>{list_markup}</ul>
    </main>
  </body>
</html>
"""
        (self.site_root / "index.html").write_text(landing_html, encoding="utf-8")
        return entries


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mirror official or primary web documentation into Nova School reference packs.")
    parser.add_argument("--pack", choices=sorted(MIRROR_PACKS), help="Import exactly one configured reference pack.")
    parser.add_argument("--all", action="store_true", help="Import all configured reference packs.")
    parser.add_argument(
        "--output-root",
        default=r"D:\Nova_school_server\data\reference_library\packs",
        help="Target packs directory.",
    )
    parser.add_argument("--clean", action="store_true", help="Delete an existing pack site before importing.")
    parser.add_argument("--finalize-only", action="store_true", help="Skip downloads and only rewrite/index an already downloaded site.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if not args.all and not args.pack:
        parser.error("Bitte entweder --pack <slug> oder --all angeben.")

    output_root = Path(args.output_root)
    selected = sorted(MIRROR_PACKS) if args.all else [str(args.pack)]
    manifests: dict[str, object] = {}
    for slug in selected:
        pack = MIRROR_PACKS[slug]
        builder = ReferenceWebMirrorBuilder(pack=pack, output_root=output_root / slug, clean=bool(args.clean))
        manifests[slug] = builder.finalize_existing_site() if args.finalize_only else builder.build()
    print(json.dumps(manifests, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

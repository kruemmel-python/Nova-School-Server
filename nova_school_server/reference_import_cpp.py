from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import time
import urllib.request
from collections import deque
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Iterable
from urllib.parse import SplitResult, quote, unquote, urljoin, urlsplit, urlunsplit


CPPREFERENCE_BASE = "https://en.cppreference.com"
CPPREFERENCE_HOST = "en.cppreference.com"
CPPREFERENCE_UPLOAD_HOST = "upload.cppreference.com"

DEFAULT_SEEDS: dict[str, str] = {
    "00_cpp": "/w/cpp",
    "01_language": "/w/cpp/language",
    "02_containers": "/w/cpp/container",
    "03_strings": "/w/cpp/string",
    "04_algorithms": "/w/cpp/algorithm",
    "05_memory": "/w/cpp/memory",
    "06_threads": "/w/cpp/thread",
}

INLINE_SCRIPT_RE = re.compile(r"(?is)<script\b[^>]*>.*?</script>")
STYLE_TAG_RE = re.compile(r"(?is)<style\b[^>]*>(.*?)</style>")
ATTR_RE = re.compile(
    r"(?P<attr>\b(?:href|src|poster|action)=)(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
    flags=re.IGNORECASE | re.DOTALL,
)
SRCSET_RE = re.compile(
    r"(?P<attr>\bsrcset=)(?P<quote>[\"'])(?P<value>.*?)(?P=quote)",
    flags=re.IGNORECASE | re.DOTALL,
)
CSS_URL_RE = re.compile(r"url\((?P<quote>[\"']?)(?P<value>.*?)(?P=quote)\)", flags=re.IGNORECASE)
TITLE_RE = re.compile(r"<title[^>]*>(?P<title>.*?)</title>", flags=re.IGNORECASE | re.DOTALL)

STATIC_ASSET_SUFFIXES = (".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".htc", ".woff", ".woff2", ".ttf", ".eot")


@dataclass(frozen=True, slots=True)
class ReferenceTarget:
    kind: str
    url: str
    local_path: str
    fragment: str = ""


class CppReferenceMirrorBuilder:
    def __init__(
        self,
        *,
        output_root: Path,
        page_limit: int = 1200,
        asset_limit: int = 400,
        delay_seconds: float = 0.0,
        timeout_seconds: int = 25,
        clean: bool = False,
        seeds: dict[str, str] | None = None,
    ) -> None:
        self.output_root = output_root
        self.site_root = self.output_root / "site"
        self.meta_path = self.output_root / "cppreference_manifest.json"
        self.page_limit = max(1, int(page_limit))
        self.asset_limit = max(0, int(asset_limit))
        self.delay_seconds = max(0.0, float(delay_seconds))
        self.timeout_seconds = max(5, int(timeout_seconds))
        self.clean = clean
        self.seeds = seeds or dict(DEFAULT_SEEDS)
        self.page_seen: set[str] = set()
        self.asset_seen: set[str] = set()
        self.page_queue: deque[str] = deque()
        self.asset_queue: deque[str] = deque()
        self.page_count = 0
        self.asset_count = 0
        self.errors: list[dict[str, str]] = []

    def build(self) -> dict[str, object]:
        self._prepare_output()
        for remote_url in self._seed_urls():
            self.page_queue.append(remote_url)

        while self.page_queue and self.page_count < self.page_limit:
            remote_url = self.page_queue.popleft()
            if remote_url in self.page_seen:
                continue
            self._mirror_page(remote_url)

        while self.asset_queue and self.asset_count < self.asset_limit:
            remote_url = self.asset_queue.popleft()
            if remote_url in self.asset_seen:
                continue
            self._mirror_asset(remote_url)

        self._write_landing_page()
        manifest = {
            "source": CPPREFERENCE_BASE,
            "page_limit": self.page_limit,
            "asset_limit": self.asset_limit,
            "pages_mirrored": self.page_count,
            "assets_mirrored": self.asset_count,
            "errors": self.errors,
            "generated_at_epoch": int(time.time()),
        }
        self.meta_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest

    def _prepare_output(self) -> None:
        self.output_root.mkdir(parents=True, exist_ok=True)
        if self.clean and self.site_root.exists():
            shutil.rmtree(self.site_root)
        self.site_root.mkdir(parents=True, exist_ok=True)

    def _seed_urls(self) -> list[str]:
        urls: list[str] = []
        for raw_path in self.seeds.values():
            target = self.classify_reference(raw_path, base_url=CPPREFERENCE_BASE, attribute="href")
            if target and target.kind == "page":
                urls.append(target.url)
        return urls

    def _mirror_page(self, remote_url: str) -> None:
        body = self._fetch(remote_url)
        if body is None:
            self.page_seen.add(remote_url)
            return
        rewritten_html = self._rewrite_html(body.decode("utf-8", errors="ignore"), remote_url)
        local_path = self.site_root / self.local_page_path(remote_url)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text(rewritten_html, encoding="utf-8")
        self.page_seen.add(remote_url)
        self.page_count += 1

    def _mirror_asset(self, remote_url: str) -> None:
        payload = self._fetch(remote_url)
        if payload is None:
            self.asset_seen.add(remote_url)
            return
        local_path = self.site_root / self.local_asset_path(remote_url)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        if self._is_css_asset(remote_url):
            css = payload.decode("utf-8", errors="ignore")
            css = self._rewrite_css(css, remote_url, local_path)
            local_path.write_text(css, encoding="utf-8")
        else:
            local_path.write_bytes(payload)
        self.asset_seen.add(remote_url)
        self.asset_count += 1

    def _fetch(self, remote_url: str) -> bytes | None:
        request = urllib.request.Request(
            remote_url,
            headers={
                "User-Agent": "NovaSchoolServer/1.0 (+offline reference import)",
                "Accept": "*/*",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                payload = response.read()
        except Exception as exc:
            self.errors.append({"url": remote_url, "error": str(exc)})
            return None
        if self.delay_seconds:
            time.sleep(self.delay_seconds)
        return payload

    def _rewrite_html(self, html_text: str, current_url: str) -> str:
        sanitized = INLINE_SCRIPT_RE.sub("", html_text)
        sanitized = self._strip_external_noise(sanitized)
        current_local_path = self.local_page_path(current_url)

        def replace_attr(match: re.Match[str]) -> str:
            attr = match.group("attr")
            quote = match.group("quote")
            value = html.unescape(match.group("value"))
            rewritten = self._rewrite_reference(
                value,
                base_url=current_url,
                current_local_path=current_local_path,
                attribute=attr[:-1].lower(),
            )
            if rewritten is None:
                rewritten = "#"
            return f"{attr}{quote}{html.escape(rewritten, quote=True)}{quote}"

        sanitized = ATTR_RE.sub(replace_attr, sanitized)
        sanitized = SRCSET_RE.sub(lambda match: self._rewrite_srcset(match, current_url, current_local_path), sanitized)
        sanitized = STYLE_TAG_RE.sub(lambda match: f"<style>{self._rewrite_css(match.group(1), current_url, current_local_path)}</style>", sanitized)
        return sanitized

    def _rewrite_srcset(self, match: re.Match[str], current_url: str, current_local_path: Path) -> str:
        attr = match.group("attr")
        quote = match.group("quote")
        items: list[str] = []
        for raw_item in match.group("value").split(","):
            parts = raw_item.strip().split()
            if not parts:
                continue
            url_value = html.unescape(parts[0])
            rewritten = self._rewrite_reference(url_value, base_url=current_url, current_local_path=current_local_path, attribute="src")
            if rewritten is None:
                continue
            if len(parts) > 1:
                items.append(f"{rewritten} {' '.join(parts[1:])}")
            else:
                items.append(rewritten)
        return f"{attr}{quote}{html.escape(', '.join(items), quote=True)}{quote}"

    def _rewrite_css(self, css_text: str, current_url: str, current_local_path: Path) -> str:
        def replace_url(match: re.Match[str]) -> str:
            quote = match.group("quote") or ""
            value = html.unescape(match.group("value").strip())
            rewritten = self._rewrite_reference(value, base_url=current_url, current_local_path=current_local_path, attribute="css")
            if rewritten is None:
                return "url()"
            return f"url({quote}{rewritten}{quote})"

        return CSS_URL_RE.sub(replace_url, css_text)

    def _rewrite_reference(self, raw_value: str, *, base_url: str, current_local_path: Path, attribute: str) -> str | None:
        target = self.classify_reference(raw_value, base_url=base_url, attribute=attribute)
        if target is None:
            return None
        if target.kind == "fragment":
            return f"#{target.fragment}" if target.fragment else "#"
        if target.kind == "page":
            if target.url not in self.page_seen:
                self.page_queue.append(target.url)
        elif target.kind == "asset":
            if target.url not in self.asset_seen:
                self.asset_queue.append(target.url)
        target_local = Path(target.local_path)
        return self._relative_href(current_local_path, target_local, target.fragment)

    @staticmethod
    def classify_reference(raw_value: str, *, base_url: str, attribute: str) -> ReferenceTarget | None:
        value = (raw_value or "").strip()
        if not value:
            return None
        if value.startswith("#"):
            return ReferenceTarget(kind="fragment", url=base_url, local_path="", fragment=value[1:])
        if attribute == "action":
            return None

        lowered = value.lower()
        if lowered.startswith(("javascript:", "mailto:", "tel:", "data:")):
            return None

        joined = urljoin(base_url, value)
        parsed = urlsplit(joined)
        fragment = parsed.fragment or ""
        parsed = SplitResult(parsed.scheme or "https", parsed.netloc or CPPREFERENCE_HOST, parsed.path, parsed.query, "")
        host = parsed.netloc.lower()
        path = parsed.path or "/"

        if host not in {CPPREFERENCE_HOST, CPPREFERENCE_UPLOAD_HOST}:
            return None

        if host == CPPREFERENCE_UPLOAD_HOST:
            if not path.startswith("/mwiki/images/"):
                return None
            local_path = Path("_external") / CPPREFERENCE_UPLOAD_HOST / unquote(path.lstrip("/"))
            return ReferenceTarget(kind="asset", url=urlunsplit(parsed), local_path=local_path.as_posix(), fragment=fragment)

        if path in {"/favicon.ico", "/favicon.ico/"}:
            return ReferenceTarget(kind="asset", url=urlunsplit(parsed), local_path="favicon.ico", fragment=fragment)

        if path.startswith("/mwiki/"):
            normalized_asset_path = path.lower()
            is_supported_asset = (
                normalized_asset_path.startswith("/mwiki/skins/")
                or normalized_asset_path.startswith("/mwiki/images/")
                or normalized_asset_path.startswith("/mwiki/load.php")
                or normalized_asset_path.endswith(STATIC_ASSET_SUFFIXES)
            )
            if not is_supported_asset:
                return None
            local_path = Path(unquote(path.lstrip("/")))
            if parsed.query:
                suffix = local_path.suffix
                stem = local_path.stem or "asset"
                hashed = sha1(parsed.query.encode("utf-8")).hexdigest()[:12]
                local_path = local_path.with_name(f"{stem}__{hashed}{suffix}")
            return ReferenceTarget(kind="asset", url=urlunsplit(parsed), local_path=local_path.as_posix(), fragment=fragment)

        normalized_page_path = CppReferenceMirrorBuilder._normalize_cpp_page_path(path)
        if normalized_page_path is None:
            return None
        local_path = CppReferenceMirrorBuilder.local_page_path(urlunsplit(("https", CPPREFERENCE_HOST, normalized_page_path, "", "")))
        return ReferenceTarget(kind="page", url=urlunsplit(("https", CPPREFERENCE_HOST, normalized_page_path, "", "")), local_path=local_path.as_posix(), fragment=fragment)

    @staticmethod
    def _normalize_cpp_page_path(path: str) -> str | None:
        clean_path = path.rstrip("/") or "/"
        if clean_path == "/w/cpp.html":
            return "/w/cpp"
        if clean_path.endswith(".html") and clean_path.startswith("/w/"):
            clean_path = clean_path[:-5]
        if clean_path == "/w/cpp":
            return clean_path
        if clean_path.startswith("/w/cpp/"):
            if ":" in clean_path:
                return None
            return clean_path
        return None

    @staticmethod
    def local_page_path(remote_url: str) -> Path:
        parsed = urlsplit(remote_url)
        normalized = CppReferenceMirrorBuilder._normalize_cpp_page_path(parsed.path or "/w/cpp")
        if normalized is None:
            raise ValueError(f"Unsupported cpp page url: {remote_url}")
        if normalized == "/w/cpp":
            return Path("w") / "cpp.html"
        return Path(normalized.lstrip("/") + ".html")

    @staticmethod
    def local_asset_path(remote_url: str) -> Path:
        target = CppReferenceMirrorBuilder.classify_reference(remote_url, base_url=CPPREFERENCE_BASE, attribute="src")
        if target is None or target.kind != "asset":
            raise ValueError(f"Unsupported asset url: {remote_url}")
        return Path(target.local_path)

    @staticmethod
    def _relative_href(current_local_path: Path, target_local_path: Path, fragment: str) -> str:
        relative = Path(shutil.os.path.relpath(target_local_path, current_local_path.parent)).as_posix()
        encoded_relative = "/".join(quote(part, safe="") for part in relative.split("/"))
        if fragment:
            return f"{encoded_relative}#{fragment}"
        return encoded_relative

    @staticmethod
    def _is_css_asset(remote_url: str) -> bool:
        parsed = urlsplit(remote_url)
        path = parsed.path.lower()
        if path.endswith(".css"):
            return True
        return "only=styles" in remote_url or "skins.cppreference2" in remote_url and path.endswith("load.php")

    @staticmethod
    def _strip_external_noise(html_text: str) -> str:
        cleaned = html_text
        cleaned = re.sub(r"(?is)<script[^>]+cdn\.carbonads\.com[^>]*>.*?</script>", "", cleaned)
        cleaned = re.sub(r"(?is)<script[^>]+googletagmanager\.com[^>]*>.*?</script>", "", cleaned)
        cleaned = re.sub(r"(?is)<div id=\"carbonads\".*?</div>\s*</div>", "", cleaned)
        cleaned = re.sub(r"(?is)<form action=\"https://duckduckgo\.com/\".*?</form>", "<div class=\"nova-offline-note\">Offline-Mirror: Websuche wurde fuer die lokale Nutzung deaktiviert.</div>", cleaned)
        return cleaned

    def _write_landing_page(self) -> None:
        links = []
        for name, raw_path in self.seeds.items():
            target = self.classify_reference(raw_path, base_url=CPPREFERENCE_BASE, attribute="href")
            if target is None or target.kind != "page":
                continue
            title = name.replace("_", " ").strip()
            label = title.split(" ", 1)[1] if " " in title else title
            links.append(
                f'<li><a href="{html.escape(self._relative_href(Path("index.html"), Path(target.local_path), ""))}">{html.escape(label)}</a></li>'
            )
        landing = f"""<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>C++ Offline Mirror</title>
    <style>
      body {{ font-family: Georgia, "Times New Roman", serif; margin: 0; padding: 2rem; color: #182126; background: #fcfaf5; }}
      main {{ max-width: 960px; margin: 0 auto; }}
      h1 {{ margin-top: 0; }}
      .note {{ padding: 1rem 1.2rem; border-radius: 18px; background: #e6f1ee; color: #0a4d49; }}
      ul {{ line-height: 1.8; }}
      code {{ font-family: "Cascadia Code", Consolas, monospace; }}
    </style>
  </head>
  <body>
    <main>
      <h1>C++ Offline Mirror</h1>
      <p class="note">Dieses Paket ist ein lokal ausgeliefertes HTML-Mirror von <code>cppreference.com</code> fuer den Nova School Server. Interne Navigationslinks bleiben offline verfuegbar.</p>
      <h2>Einstieg</h2>
      <ul>
        {''.join(links)}
      </ul>
    </main>
  </body>
</html>
"""
        (self.site_root / "index.html").write_text(landing, encoding="utf-8")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Mirror cppreference C++ pages into the Nova School offline reference library.")
    parser.add_argument(
        "--output",
        default=r"D:\Nova_school_server\data\reference_library\packs\cpp",
        help="Target pack directory. The HTML mirror will be written into the site subfolder.",
    )
    parser.add_argument("--page-limit", type=int, default=1200, help="Maximum number of HTML pages to mirror.")
    parser.add_argument("--asset-limit", type=int, default=400, help="Maximum number of local CSS/image assets to mirror.")
    parser.add_argument("--delay", type=float, default=0.0, help="Optional delay between requests in seconds.")
    parser.add_argument("--timeout", type=int, default=25, help="HTTP timeout per request in seconds.")
    parser.add_argument("--clean", action="store_true", help="Remove an existing site mirror before importing.")
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    builder = CppReferenceMirrorBuilder(
        output_root=Path(args.output),
        page_limit=args.page_limit,
        asset_limit=args.asset_limit,
        delay_seconds=args.delay,
        timeout_seconds=args.timeout,
        clean=args.clean,
    )
    manifest = builder.build()
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

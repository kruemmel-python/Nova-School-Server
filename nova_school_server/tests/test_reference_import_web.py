from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nova_school_server.reference_import_web import MIRROR_PACKS, ReferenceWebMirrorBuilder


class ReferenceWebImportTests(unittest.TestCase):
    def test_resolve_local_target_finds_html_and_assets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site_root = root / "site" / "developer.mozilla.org" / "en-US" / "docs" / "Web"
            site_root.mkdir(parents=True, exist_ok=True)
            (site_root / "JavaScript.html").write_text("<html></html>", encoding="utf-8")
            static_root = root / "site" / "developer.mozilla.org" / "static" / "client"
            static_root.mkdir(parents=True, exist_ok=True)
            (static_root / "runtime.js").write_text("console.log('ok');", encoding="utf-8")

            builder = ReferenceWebMirrorBuilder(pack=MIRROR_PACKS["javascript"], output_root=root)

            self.assertEqual(
                builder.resolve_local_target("https://developer.mozilla.org/en-US/docs/Web/JavaScript"),
                site_root / "JavaScript.html",
            )
            self.assertEqual(
                builder.resolve_local_target("/static/client/runtime.js"),
                static_root / "runtime.js",
            )

    def test_html_rewrite_localizes_absolute_pack_urls(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host_root = root / "site" / "doc.rust-lang.org"
            current = host_root / "reference" / "index.html"
            current.parent.mkdir(parents=True, exist_ok=True)
            current.write_text(
                '<html><head><link rel="stylesheet" href="/static.files/rustdoc.css"></head>'
                '<body><a href="https://doc.rust-lang.org/std/index.html">std</a>'
                '<img src="/static.files/logo.svg"></body></html>',
                encoding="utf-8",
            )
            static_root = host_root / "static.files"
            static_root.mkdir(parents=True, exist_ok=True)
            (static_root / "rustdoc.css").write_text("body{}", encoding="utf-8")
            (static_root / "logo.svg").write_text("<svg></svg>", encoding="utf-8")
            std_root = host_root / "std"
            std_root.mkdir(parents=True, exist_ok=True)
            (std_root / "index.html").write_text("<html></html>", encoding="utf-8")

            builder = ReferenceWebMirrorBuilder(pack=MIRROR_PACKS["rust"], output_root=root)
            builder._rewrite_mirror_html()
            rewritten = current.read_text(encoding="utf-8")

            self.assertIn('href="../std/index.html"', rewritten)
            self.assertIn('href="../static.files/rustdoc.css"', rewritten)
            self.assertIn('src="../static.files/logo.svg"', rewritten)

    def test_landing_page_links_to_mirrored_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site_root = root / "site" / "dev.java" / "learn"
            site_root.mkdir(parents=True, exist_ok=True)
            (site_root / "index.html").write_text("<html></html>", encoding="utf-8")
            api_root = root / "site" / "docs.oracle.com" / "en" / "java" / "javase" / "21" / "docs" / "api"
            api_root.mkdir(parents=True, exist_ok=True)
            (api_root / "index.html").write_text("<html></html>", encoding="utf-8")

            builder = ReferenceWebMirrorBuilder(pack=MIRROR_PACKS["java"], output_root=root)
            entries = builder._write_landing_page()
            landing = (root / "site" / "index.html").read_text(encoding="utf-8")

            self.assertEqual(len(entries), 2)
            self.assertIn("Dev.java Learn", landing)
            self.assertIn("docs.oracle.com/en/java/javase/21/docs/api/index.html", landing)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nova_school_server.reference_import_cpp import CppReferenceMirrorBuilder


class CppReferenceImportTests(unittest.TestCase):
    def test_cpp_page_urls_are_normalized_to_local_html_paths(self) -> None:
        target = CppReferenceMirrorBuilder.classify_reference(
            "https://en.cppreference.com/w/cpp/string/basic_string.html",
            base_url="https://en.cppreference.com/w/cpp/string",
            attribute="href",
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.kind, "page")
        self.assertEqual(target.url, "https://en.cppreference.com/w/cpp/string/basic_string")
        self.assertEqual(target.local_path, "w/cpp/string/basic_string.html")

    def test_cpp_assets_are_classified_and_localized(self) -> None:
        target = CppReferenceMirrorBuilder.classify_reference(
            "/mwiki/load.php@debug=false&lang=en&only=styles&skin=cppreference2&%252A.css",
            base_url="https://en.cppreference.com/w/cpp/string",
            attribute="href",
        )
        self.assertIsNotNone(target)
        assert target is not None
        self.assertEqual(target.kind, "asset")
        self.assertEqual(
            target.local_path,
            "mwiki/load.php@debug=false&lang=en&only=styles&skin=cppreference2&%2A.css",
        )

    def test_mediawiki_edit_links_and_form_actions_are_ignored(self) -> None:
        edit_link = CppReferenceMirrorBuilder.classify_reference(
            "https://en.cppreference.com/mwiki/index.php?title=cpp/string&action=edit",
            base_url="https://en.cppreference.com/w/cpp/string",
            attribute="href",
        )
        form_action = CppReferenceMirrorBuilder.classify_reference(
            "https://duckduckgo.com/",
            base_url="https://en.cppreference.com/w/cpp/string",
            attribute="action",
        )
        self.assertIsNone(edit_link)
        self.assertIsNone(form_action)

    def test_html_rewriter_keeps_internal_links_local_and_disables_external_links(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            builder = CppReferenceMirrorBuilder(output_root=Path(tmp))
            html = """
            <html><head>
            <link rel="stylesheet" href="/mwiki/load.php@debug=false&lang=en&only=styles&skin=cppreference2&%252A.css" />
            <script src="https://cdn.carbonads.com/carbon.js?serve=test"></script>
            </head><body>
            <a href="string/basic_string.html">basic_string</a>
            <a href="https://example.com/">external</a>
            <img src="https://upload.cppreference.com/mwiki/images/test.png" />
            </body></html>
            """
            rewritten = builder._rewrite_html(html, "https://en.cppreference.com/w/cpp/string")
            self.assertIn('href="string/basic_string.html"', rewritten)
            self.assertIn('href="#"', rewritten)
            self.assertIn(
                '../../mwiki/load.php%40debug%3Dfalse%26lang%3Den%26only%3Dstyles%26skin%3Dcppreference2%26%252A.css',
                rewritten,
            )
            self.assertIn('../../_external/upload.cppreference.com/mwiki/images/test.png', rewritten)
            self.assertNotIn("carbonads.com", rewritten)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from nova_school_server.reference_library import ReferenceLibraryService


class ReferenceLibraryTests(unittest.TestCase):
    def test_builtin_fallback_catalog_and_search_work(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            service = ReferenceLibraryService(Path(tmp))
            catalog = service.catalog()
            python_entry = next(item for item in catalog if item["slug"] == "python")

            self.assertEqual(python_entry["status"], "starter")
            self.assertGreaterEqual(python_entry["doc_count"], 1)

            results = service.search("sum", area="python", limit=10)
            self.assertTrue(any(item["area"] == "python" for item in results))

            portal = service.render_portal(area="python", query="python")
            self.assertIn("Offline Referenzbibliothek", portal)
            self.assertIn("Python", portal)
            self.assertIn("data-reference-sidebar-toggle", portal)
            self.assertIn("data-reference-wide-toggle", portal)
            self.assertIn("/static/reference.js", portal)

    def test_mirrored_pack_is_indexed_and_asset_path_is_resolved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site_root = root / "packs" / "python" / "site"
            site_root.mkdir(parents=True, exist_ok=True)
            (site_root / "index.html").write_text(
                "<html><head><title>Python Mirror</title></head><body><h1>Python Mirror</h1><p>list comprehensions and generators</p></body></html>",
                encoding="utf-8",
            )

            service = ReferenceLibraryService(root)
            docs = service.documents("python", limit=10)
            self.assertEqual(docs[0]["status"], "mirrored")
            self.assertEqual(docs[0]["viewer"], "iframe")

            results = service.search("generators", area="python", limit=10)
            self.assertEqual(results[0]["doc_id"], "index.html")

            asset = service.resolve_asset("python", "index.html")
            self.assertTrue(asset.exists())

    def test_plain_text_pack_directly_in_area_root_is_used(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_root = root / "packs" / "python"
            pack_root.mkdir(parents=True, exist_ok=True)
            (pack_root / "contents.txt").write_text(
                "Python Documentation\n\nThe built-in sum() function adds an iterable of numbers.",
                encoding="utf-8",
            )

            service = ReferenceLibraryService(root)
            catalog = next(item for item in service.catalog() if item["slug"] == "python")

            self.assertEqual(catalog["status"], "mirrored")
            self.assertEqual(catalog["install_path"], str(pack_root))

            docs = service.documents("python", limit=10)
            self.assertEqual(docs[0]["status"], "mirrored")
            self.assertEqual(docs[0]["content_type"], "text")
            self.assertEqual(docs[0]["doc_id"], "contents.txt")

            results = service.search("sum", area="python", limit=10)
            self.assertTrue(any(item["doc_id"] == "contents.txt" for item in results))

    def test_index_is_rebuilt_when_pack_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_root = root / "packs" / "python"
            pack_root.mkdir(parents=True, exist_ok=True)
            (pack_root / "alpha.txt").write_text("Alpha documentation", encoding="utf-8")

            service = ReferenceLibraryService(root)
            first_docs = service.documents("python", limit=10)
            self.assertEqual(len(first_docs), 1)

            time.sleep(0.02)
            (pack_root / "beta.txt").write_text("Beta documentation with itertools", encoding="utf-8")

            second_docs = service.documents("python", limit=10)
            self.assertEqual(len(second_docs), 2)
            self.assertTrue(any(item["doc_id"] == "beta.txt" for item in second_docs))

    def test_cpp_markdown_mirror_is_sanitized_for_rendering(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pack_root = root / "packs" / "cpp" / "03_strings"
            pack_root.mkdir(parents=True, exist_ok=True)
            (pack_root / "string.md").write_text(
                (
                    "C++ Compiler support Language Standard library External libraries [edit] "
                    "Strings library Classes basic_string basic_string_view (C++17) char_traits [edit]\n"
                    "## Contents\n"
                    "- 1 Characters\n"
                    "- 2 Library components\n"
                    "### [ edit ] Characters In the C++ standard library, a character is an object.\n"
                    "[edit] Library components The C++ strings library includes the following components.\n"
                    "[edit] Character traits Many character-related class templates need a set of related types.\n"
                ),
                encoding="utf-8",
            )

            service = ReferenceLibraryService(root)
            docs = service.documents("cpp", limit=10)
            string_doc = next(item for item in docs if item["doc_id"] == "03_strings/string.md")

            self.assertEqual(string_doc["title"], "Strings Library")
            self.assertIn("# Strings Library", string_doc["render_content"])
            self.assertIn("### Characters", string_doc["render_content"])
            self.assertIn("### Library components", string_doc["render_content"])
            self.assertNotIn("[edit]", string_doc["render_content"])


if __name__ == "__main__":
    unittest.main()

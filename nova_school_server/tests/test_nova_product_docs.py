from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from nova_school_server.nova_product_docs import NovaSchoolProductDocsBuilder
from nova_school_server.reference_library import ReferenceLibraryService


class NovaProductDocsTests(unittest.TestCase):
    def test_builder_generates_index_and_expands_permission_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "docs" / "nova_school"
            pack_root = root / "reference_library" / "packs" / "nova-school"
            source_root.mkdir(parents=True, exist_ok=True)
            (source_root / "01_Test.md").write_text(
                (
                    "# Testdokument\n\n"
                    "Kurze Einordnung fuer das System.\n\n"
                    "{{PERMISSION_TABLE}}\n\n"
                    "{{ROLE_DEFAULTS_TABLE}}\n"
                ),
                encoding="utf-8",
            )

            builder = NovaSchoolProductDocsBuilder(source_root=source_root, pack_root=pack_root)
            builder.build()

            built_doc = (pack_root / "site" / "01_Test.md").read_text(encoding="utf-8")
            built_index = (pack_root / "site" / "index.md").read_text(encoding="utf-8")
            manifest = json.loads((pack_root / "manifest.json").read_text(encoding="utf-8"))

            self.assertIn("`project.create`", built_doc)
            self.assertIn("| Recht | Student | Teacher | Admin |", built_doc)
            self.assertIn("/reference?area=nova-school&doc=01_Test.md", built_index)
            self.assertEqual(manifest["document_count"], 2)

    def test_reference_library_marks_nova_school_as_official_local(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source_root = root / "docs" / "nova_school"
            source_root.mkdir(parents=True, exist_ok=True)
            (source_root / "01_System.md").write_text(
                "# Systemreferenz\n\nNova School vereint Audit, Container und Unterrichtsbetrieb.\n",
                encoding="utf-8",
            )

            service = ReferenceLibraryService(root / "reference_library", docs_source_root=source_root)
            catalog = next(item for item in service.catalog() if item["slug"] == "nova-school")

            self.assertEqual(catalog["status"], "official-local")
            self.assertGreaterEqual(catalog["doc_count"], 2)

            docs = service.documents("nova-school", limit=10)
            self.assertTrue(any(item["doc_id"] == "01_System.md" for item in docs))

            results = service.search("container", area="nova-school", limit=10)
            self.assertTrue(any(item["doc_id"] == "01_System.md" for item in results))

            portal = service.render_portal(area="nova-school", doc_id="01_System.md", query="audit")
            self.assertIn("Nova School Produktdokumentation", portal)
            self.assertIn("official-local", portal)


if __name__ == "__main__":
    unittest.main()

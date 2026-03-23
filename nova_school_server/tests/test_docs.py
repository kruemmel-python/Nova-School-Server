from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nova_school_server.docs_catalog import DocumentationCatalog


class DocumentationTests(unittest.TestCase):
    def test_seed_docs_and_read_python_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            catalog = DocumentationCatalog(Path(tmp))
            catalog.ensure_seed_docs()
            docs = catalog.list_docs()
            self.assertTrue(any(item["slug"] == "python" for item in docs))
            python_doc = catalog.get_doc("python")
            self.assertIn("Python Schnellstart", python_doc["title"])
            self.assertIn("python", python_doc["content"].lower())


if __name__ == "__main__":
    unittest.main()

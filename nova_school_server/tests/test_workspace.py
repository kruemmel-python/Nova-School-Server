from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import json

from nova_school_server.config import ServerConfig
from nova_school_server.workspace import WorkspaceManager


class WorkspaceTests(unittest.TestCase):
    def test_materialize_project_and_block_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            manager = WorkspaceManager(config)
            project = {
                "owner_type": "user",
                "owner_key": "student",
                "slug": "python-labor",
                "template": "python",
            }
            root = manager.materialize_project(project)
            self.assertTrue((root / "main.py").exists())
            with self.assertRaises(ValueError):
                manager.resolve_project_path(project, "..\\..\\evil.txt")

    def test_load_notebook_normalizes_legacy_starter_cells(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            manager = WorkspaceManager(config)
            project = {
                "owner_type": "user",
                "owner_key": "student",
                "slug": "python-labor",
                "template": "python",
            }
            root = manager.materialize_project(project)
            notebook_path = root / ".nova-school" / "notebook.json"
            notebook_path.write_text(
                json.dumps(
                    [
                        {
                            "id": "py-1",
                            "title": "Python Zelle",
                            "language": "python",
                            "code": "numbers = [1, 2, 3, 4]\\nprint(sum(numbers))\\n",
                        }
                    ],
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            cells = manager.load_notebook(project)

            self.assertEqual(cells[0]["code"], "numbers = [1, 2, 3, 4]\nprint(sum(numbers))\n")
            persisted = json.loads(notebook_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted[0]["code"], "numbers = [1, 2, 3, 4]\nprint(sum(numbers))\n")


if __name__ == "__main__":
    unittest.main()

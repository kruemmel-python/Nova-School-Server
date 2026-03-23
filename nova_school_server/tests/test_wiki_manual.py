from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nova_school_server.wiki_manual import WikiManualService


class _Session:
    def __init__(self, role: str) -> None:
        self.role = role
        self.user = {"display_name": "Test User"}

    @property
    def is_teacher(self) -> bool:
        return self.role in {"teacher", "admin"}


class WikiManualTests(unittest.TestCase):
    def test_student_gets_student_manual_and_markdown_is_rendered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            teacher_root = wiki_root / "Lehrer_Admin"
            student_root = wiki_root / "Schüler_User"
            teacher_root.mkdir(parents=True, exist_ok=True)
            student_root.mkdir(parents=True, exist_ok=True)

            (teacher_root / "README.md").write_text("# Lehrer\n\nNur intern.\n", encoding="utf-8")
            (student_root / "README.md").write_text(
                "\n".join(
                    [
                        "# Schüler-Handbuch",
                        "",
                        "Siehe [Kapitel 1](./01_Start.md).",
                        "",
                        "## Übersicht",
                        "",
                        "| Spalte | Wert |",
                        "| --- | --- |",
                        "| Rolle | Schüler |",
                        "",
                        "```python",
                        "print('Nova')",
                        "```",
                    ]
                ),
                encoding="utf-8",
            )
            (student_root / "01_Start.md").write_text("# Start\n\n- Punkt A\n", encoding="utf-8")

            service = WikiManualService(wiki_root)
            html = service.render_page(_Session("student"), requested_scope="teacher-admin", requested_page="README")

            self.assertIn("Schüler-Handbuch", html)
            self.assertIn("/manual?scope=student-user&amp;page=01_Start", html)
            self.assertIn('<table class="manual-table">', html)
            self.assertIn('<pre class="manual-code"><code data-language="python">', html)
            self.assertNotIn("Nur intern.", html)

    def test_teacher_can_switch_to_teacher_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            wiki_root = Path(tmp)
            teacher_root = wiki_root / "Lehrer_Admin"
            student_root = wiki_root / "Schüler_User"
            teacher_root.mkdir(parents=True, exist_ok=True)
            student_root.mkdir(parents=True, exist_ok=True)

            (teacher_root / "README.md").write_text("# Lehrkraft\n\n## Start\n\n1. Prüfen\n", encoding="utf-8")
            (student_root / "README.md").write_text("# Schüler\n", encoding="utf-8")

            service = WikiManualService(wiki_root)
            html = service.render_page(_Session("teacher"), requested_scope="teacher-admin", requested_page="README")

            self.assertIn("Lehrkraft", html)
            self.assertIn("Lehrkräfte und Administration", html)
            self.assertIn("/manual?scope=student-user", html)
            self.assertIn('href="#start"', html)


if __name__ == "__main__":
    unittest.main()

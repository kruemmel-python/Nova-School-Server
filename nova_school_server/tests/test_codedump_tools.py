from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from nova_school_server.codedump_tools import (
    DumpConfig,
    collect_directory_dump,
    config_for_profile,
    default_output_path_for_profile,
    dump_target_to_markdown,
)


class CodeDumpToolsTests(unittest.TestCase):
    def test_directory_dump_ignores_runtime_data_and_writes_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir(parents=True, exist_ok=True)
            (root / "main.py").write_text("print('hello')\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            (root / "data" / "reference_library").mkdir(parents=True, exist_ok=True)
            (root / "data" / "reference_library" / "index.json").write_text("{}", encoding="utf-8")

            output_path = root / "CODEDUMP.md"
            output_path.write_text("stale dump", encoding="utf-8")
            dump_target_to_markdown(root, output_path)
            content = output_path.read_text(encoding="utf-8")

            self.assertIn("# Code Dump: project", content)
            self.assertIn("### `main.py`", content)
            self.assertIn("print('hello')", content)
            self.assertIn("## Ignorierte Bereiche", content)
            self.assertIn("`data`", content)
            self.assertNotIn("### `data/reference_library/index.json`", content)
            self.assertNotIn("### `CODEDUMP.md`", content)

    def test_zip_dump_keeps_zip_support(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive_path = root / "demo.zip"
            output_path = root / "dump.md"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("src/app.py", "print('zip')\n")
                archive.writestr("data/reference_library/index.json", "{}")

            dump_target_to_markdown(archive_path, output_path)
            content = output_path.read_text(encoding="utf-8")

            self.assertIn("### `src/app.py`", content)
            self.assertIn("print('zip')", content)
            self.assertIn("## Ignorierte Bereiche", content)
            self.assertIn("`data`", content)
            self.assertNotIn("### `data/reference_library/index.json`", content)

    def test_directory_collect_marks_large_files_with_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir(parents=True, exist_ok=True)
            (root / "big.py").write_text("x" * 80, encoding="utf-8")

            result = collect_directory_dump(root, config=DumpConfig(max_file_size=20))
            self.assertEqual(len(result.entries), 1)
            self.assertEqual(result.entries[0].status, "skipped-too-large")
            self.assertIn("file too large", result.entries[0].content)

    def test_compact_profile_excludes_docs_wiki_and_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            (root / "nova_school_server" / "tests").mkdir(parents=True, exist_ok=True)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "wiki").mkdir(parents=True, exist_ok=True)
            (root / "nova_school_server" / "server.py").write_text("print('server')\n", encoding="utf-8")
            (root / "nova_school_server" / "tests" / "test_demo.py").write_text("print('test')\n", encoding="utf-8")
            (root / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
            (root / "wiki" / "teacher.md").write_text("# Teacher\n", encoding="utf-8")

            output_path = root / "CODEDUMP.compact.md"
            dump_target_to_markdown(root, output_path, config=config_for_profile("compact"))
            content = output_path.read_text(encoding="utf-8")

            self.assertIn("- Profil: `compact`", content)
            self.assertIn("### `nova_school_server/server.py`", content)
            self.assertNotIn("### `docs/guide.md`", content)
            self.assertNotIn("### `wiki/teacher.md`", content)
            self.assertNotIn("### `nova_school_server/tests/test_demo.py`", content)

    def test_deep_profile_includes_docs_wiki_and_tests(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            (root / "nova_school_server" / "tests").mkdir(parents=True, exist_ok=True)
            (root / "docs").mkdir(parents=True, exist_ok=True)
            (root / "wiki").mkdir(parents=True, exist_ok=True)
            (root / "nova_school_server" / "server.py").write_text("print('server')\n", encoding="utf-8")
            (root / "nova_school_server" / "tests" / "test_demo.py").write_text("print('test')\n", encoding="utf-8")
            (root / "docs" / "guide.md").write_text("# Guide\n", encoding="utf-8")
            (root / "wiki" / "teacher.md").write_text("# Teacher\n", encoding="utf-8")

            output_path = root / "CODEDUMP.deep.md"
            dump_target_to_markdown(root, output_path, config=config_for_profile("deep"))
            content = output_path.read_text(encoding="utf-8")

            self.assertIn("- Profil: `deep`", content)
            self.assertIn("### `docs/guide.md`", content)
            self.assertIn("### `wiki/teacher.md`", content)
            self.assertIn("### `nova_school_server/tests/test_demo.py`", content)

    def test_default_output_path_uses_profile_suffix_for_non_standard_profiles(self) -> None:
        directory_target = Path(r"D:\Nova_school_server")
        zip_target = Path(r"D:\Nova_school_server\project.zip")

        self.assertEqual(default_output_path_for_profile(directory_target, "standard").name, "CODEDUMP.md")
        self.assertEqual(default_output_path_for_profile(directory_target, "compact").name, "CODEDUMP.compact.md")
        self.assertEqual(default_output_path_for_profile(zip_target, "deep").name, "project.deep.codedump.md")

    def test_existing_dump_artifacts_are_not_reincluded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir(parents=True, exist_ok=True)
            (root / "main.py").write_text("print('app')\n", encoding="utf-8")
            (root / "CODEDUMP.compact.md").write_text("# old dump\n", encoding="utf-8")

            output_path = root / "CODEDUMP.deep.md"
            dump_target_to_markdown(root, output_path, config=config_for_profile("deep"))
            content = output_path.read_text(encoding="utf-8")

            self.assertIn("## Ignorierte Bereiche", content)
            self.assertIn("`codedump-artifacts`", content)
            self.assertNotIn("### `CODEDUMP.compact.md`", content)


if __name__ == "__main__":
    unittest.main()

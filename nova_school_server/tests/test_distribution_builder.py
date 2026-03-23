from __future__ import annotations

import tempfile
import unittest
import zipfile
from pathlib import Path

from nova_school_server.distribution_builder import build_distribution_archive


class DistributionBuilderTests(unittest.TestCase):
    def test_distribution_archive_excludes_runtime_data_and_adds_scaffold(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")
            (root / "README.md").write_text("readme", encoding="utf-8")
            (root / "start_server.ps1").write_text("start", encoding="utf-8")
            (root / "data").mkdir()
            (root / "data" / "school.db").write_text("secret", encoding="utf-8")
            (root / "server.zip").write_text("zip", encoding="utf-8")
            (root / ".nova").mkdir()
            (root / ".nova" / "secret.txt").write_text("secret", encoding="utf-8")

            result = build_distribution_archive(root, output_dir=root)

            self.assertTrue(result.archive_path.exists())
            with zipfile.ZipFile(result.archive_path) as archive:
                names = set(archive.namelist())
            self.assertIn("Nova-School-Server-v1.2.3-distribution/README.md", names)
            self.assertIn("Nova-School-Server-v1.2.3-distribution/server_config.json.example", names)
            self.assertIn("Nova-School-Server-v1.2.3-distribution/DISTRIBUTION_README.md", names)
            self.assertIn("Nova-School-Server-v1.2.3-distribution/data/workspaces/users/.gitkeep", names)
            self.assertNotIn("Nova-School-Server-v1.2.3-distribution/data/school.db", names)
            self.assertNotIn("Nova-School-Server-v1.2.3-distribution/server.zip", names)
            self.assertNotIn("Nova-School-Server-v1.2.3-distribution/.nova/secret.txt", names)

    def test_windows_server_package_excludes_linux_scripts_and_adds_windows_guide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")
            (root / "README.md").write_text("readme", encoding="utf-8")
            (root / "start_server.ps1").write_text("start", encoding="utf-8")
            (root / "start_server.sh").write_text("start", encoding="utf-8")
            (root / "run_tests.ps1").write_text("test", encoding="utf-8")
            (root / "run_tests.sh").write_text("test", encoding="utf-8")
            (root / "start_worker.ps1").write_text("worker", encoding="utf-8")
            (root / "start_worker.sh").write_text("worker", encoding="utf-8")

            result = build_distribution_archive(root, output_dir=root, flavor="windows-server-package")

            with zipfile.ZipFile(result.archive_path) as archive:
                names = set(archive.namelist())
            self.assertIn("Nova-School-Server-v1.2.3-windows-server-package/WINDOWS_SERVER_PACKAGE.md", names)
            self.assertIn("Nova-School-Server-v1.2.3-windows-server-package/start_server.ps1", names)
            self.assertNotIn("Nova-School-Server-v1.2.3-windows-server-package/start_server.sh", names)
            self.assertNotIn("Nova-School-Server-v1.2.3-windows-server-package/run_tests.sh", names)

    def test_linux_server_package_excludes_windows_scripts_and_adds_linux_guide(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            (root / "pyproject.toml").write_text('[project]\nversion = "1.2.3"\n', encoding="utf-8")
            (root / "README.md").write_text("readme", encoding="utf-8")
            (root / "start_server.ps1").write_text("start", encoding="utf-8")
            (root / "start_server.sh").write_text("start", encoding="utf-8")
            (root / "run_tests.ps1").write_text("test", encoding="utf-8")
            (root / "run_tests.sh").write_text("test", encoding="utf-8")
            (root / "start_worker.ps1").write_text("worker", encoding="utf-8")
            (root / "start_worker.sh").write_text("worker", encoding="utf-8")

            result = build_distribution_archive(root, output_dir=root, flavor="linux-server-package")

            with zipfile.ZipFile(result.archive_path) as archive:
                names = set(archive.namelist())
            self.assertIn("Nova-School-Server-v1.2.3-linux-server-package/LINUX_SERVER_PACKAGE.md", names)
            self.assertIn("Nova-School-Server-v1.2.3-linux-server-package/start_server.sh", names)
            self.assertNotIn("Nova-School-Server-v1.2.3-linux-server-package/start_server.ps1", names)
            self.assertNotIn("Nova-School-Server-v1.2.3-linux-server-package/run_tests.ps1", names)


if __name__ == "__main__":
    unittest.main()

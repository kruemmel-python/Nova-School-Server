from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nova_school_server.container_seccomp import resolve_seccomp_profile_option


class ContainerSeccompTests(unittest.TestCase):
    def test_resolve_seccomp_profile_option_returns_native_path_for_non_docker_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "container-denylist.json"
            profile.write_text("{}", encoding="utf-8")
            option = resolve_seccomp_profile_option(profile, "podman")
            self.assertEqual(option, f"seccomp={profile.resolve(strict=False)}")

    def test_resolve_seccomp_profile_option_uses_builtin_profile_for_windows_docker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            profile = Path(tmp) / "container-denylist.json"
            profile.write_text('{"defaultAction":"SCMP_ACT_ALLOW"}', encoding="utf-8")
            with patch("nova_school_server.container_seccomp.os.name", "nt"):
                option = resolve_seccomp_profile_option(profile, "docker")
            self.assertIsNone(option)


if __name__ == "__main__":
    unittest.main()

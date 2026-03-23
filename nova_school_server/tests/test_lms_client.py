from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from nova_school_server.config import ServerConfig
from nova_school_server.database import SchoolRepository
from nova_school_server.lms_client import LMStudioService, normalize_lmstudio_base_url


class _FakeRuntime:
    def __init__(self, runtime_config=None, cwd=None) -> None:
        self.runtime_config = runtime_config or {}
        self.cwd = cwd

    def list_models(self, provider):  # pragma: no cover - not used here
        raise AssertionError("not expected")


class LMStudioClientTests(unittest.TestCase):
    def test_normalize_rewrites_unspecified_bind_host(self) -> None:
        self.assertEqual(
            normalize_lmstudio_base_url("http://0.0.0.0:1234/v1"),
            "http://127.0.0.1:1234/v1",
        )

    def test_normalize_adds_scheme_and_default_path(self) -> None:
        self.assertEqual(
            normalize_lmstudio_base_url("127.0.0.1:1234"),
            "http://127.0.0.1:1234/v1",
        )

    def test_service_base_url_uses_normalized_setting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp)
            config = ServerConfig.from_base_path(base_path)
            repository = SchoolRepository(base_path / "school.db")
            try:
                repository.put_setting("lmstudio_base_url", "http://0.0.0.0:1234/v1")
                service = LMStudioService(_FakeRuntime, repository, config)
                self.assertEqual(service.base_url, "http://127.0.0.1:1234/v1")
            finally:
                repository.close()


if __name__ == "__main__":
    unittest.main()

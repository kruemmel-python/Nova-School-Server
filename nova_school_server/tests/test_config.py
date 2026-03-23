from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from nova_school_server.config import (
    ServerConfig,
    active_runtime_config,
    load_server_config_payload,
    runtime_config_requires_restart,
    save_server_config_payload,
    stored_runtime_config,
)


class ConfigTests(unittest.TestCase):
    def test_default_host_binds_for_lan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            self.assertEqual(config.host, "0.0.0.0")

    def test_env_host_override_is_respected(self) -> None:
        previous = os.environ.get("NOVA_SCHOOL_HOST")
        try:
            os.environ["NOVA_SCHOOL_HOST"] = "127.0.0.1"
            with tempfile.TemporaryDirectory() as tmp:
                config = ServerConfig.from_base_path(Path(tmp))
                self.assertEqual(config.host, "127.0.0.1")
        finally:
            if previous is None:
                os.environ.pop("NOVA_SCHOOL_HOST", None)
            else:
                os.environ["NOVA_SCHOOL_HOST"] = previous

    def test_server_config_payload_is_saved_and_loaded(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp)
            payload = save_server_config_payload(base_path, {"host": "127.0.0.1", "port": 9999, "tenant_id": "school-x"})
            self.assertEqual(payload["host"], "127.0.0.1")
            self.assertEqual(payload["port"], 9999)
            loaded = load_server_config_payload(base_path)
            self.assertEqual(loaded["tenant_id"], "school-x")

    def test_stored_runtime_config_falls_back_to_active_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp)
            config = ServerConfig.from_base_path(base_path)
            stored = stored_runtime_config(base_path, config)
            active = active_runtime_config(config)
            self.assertEqual(stored["host"], active["host"])
            self.assertEqual(stored["port"], active["port"])
            self.assertFalse(runtime_config_requires_restart(active, stored))

    def test_runtime_config_requires_restart_when_stored_values_differ(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_path = Path(tmp)
            config = ServerConfig.from_base_path(base_path)
            save_server_config_payload(base_path, {"port": 9988, "run_timeout_seconds": 45})
            active = active_runtime_config(config)
            stored = stored_runtime_config(base_path, config)
            self.assertTrue(runtime_config_requires_restart(active, stored))


if __name__ == "__main__":
    unittest.main()

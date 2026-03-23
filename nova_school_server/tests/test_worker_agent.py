from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from nova_school_server.worker_agent import WorkerAgent


class WorkerAgentTests(unittest.TestCase):
    def test_container_command_uses_materialized_workspace_without_copy_wrapper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            work_root = Path(tmp)
            runtime_root = work_root / "job" / "workspace"
            runtime_root.mkdir(parents=True, exist_ok=True)
            (runtime_root / "main.py").write_text("print('ok')\n", encoding="utf-8")

            agent = WorkerAgent(
                server_url="http://127.0.0.1:8877",
                worker_id="lab-node-01",
                token="secret",
                advertise_host="127.0.0.1",
                work_root=work_root,
            )
            job = {
                "backend": "container",
                "payload": {
                    "runtime": "python",
                    "entrypoint": "main.py",
                    "container_runtime": "docker",
                    "container_oci_runtime": "runsc",
                    "container_image": "python:3.12-slim",
                    "env": {},
                },
            }

            with patch("nova_school_server.worker_agent.shutil.which", return_value="docker"):
                command = agent._build_command(job, runtime_root)

            self.assertIn("--runtime", command)
            self.assertIn("runsc", command)
            self.assertNotIn("/workspace-src", " ".join(command))
            self.assertNotIn("cp -a", " ".join(command))
            self.assertTrue((runtime_root.parent / "container-workspace" / "main.py").exists())


if __name__ == "__main__":
    unittest.main()

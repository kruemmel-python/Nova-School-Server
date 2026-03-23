from __future__ import annotations

import importlib.util
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from nova_school_server.code_runner import CodeRunner
from nova_school_server.config import ServerConfig
from nova_school_server.database import SchoolRepository
from nova_school_server.realtime import LiveRunManager, RealtimeClient, WebSocketConnection
from nova_school_server.workspace import WorkspaceManager


class _FakeToolSandbox:
    def authorize(self, *_args, **_kwargs):
        return {"authorized": True}


class _Session:
    username = "student"
    role = "student"
    is_teacher = False
    permissions = {
        "run.python": True,
        "run.javascript": True,
        "run.cpp": True,
        "run.java": True,
        "run.rust": True,
        "run.node": True,
        "run.npm": True,
        "run.html": True,
        "web.access": True,
        "notebook.collaborate": True,
    }


class _TeacherSession(_Session):
    username = "teacher"
    role = "teacher"
    is_teacher = True


class _RecordingConnection:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []
        self._lock = threading.Lock()

    def send_json(self, payload):
        with self._lock:
            self.events.append(dict(payload))

    def snapshot(self) -> list[dict[str, object]]:
        with self._lock:
            return list(self.events)


class _FakeSocket:
    def __init__(self, chunks=None, *, raise_timeout: bool = False) -> None:
        self.timeout = "unset"
        self.chunks = list(chunks or [])
        self.raise_timeout = raise_timeout

    def settimeout(self, value) -> None:
        self.timeout = value

    def recv(self, size: int) -> bytes:
        if self.raise_timeout:
            raise TimeoutError("timed out")
        if self.chunks:
            chunk = self.chunks.pop(0)
            return bytes(chunk[:size])
        return b""

    def sendall(self, _data: bytes) -> None:
        return

    def shutdown(self, _how) -> None:
        return

    def close(self) -> None:
        return


class RealtimeTests(unittest.TestCase):
    def test_websocket_accept_key_matches_reference(self) -> None:
        self.assertEqual(
            WebSocketConnection.accept_key("dGhlIHNhbXBsZSBub25jZQ=="),
            "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=",
        )

    def test_websocket_connection_is_long_lived_without_idle_timeout(self) -> None:
        fake_socket = _FakeSocket()
        connection = WebSocketConnection(fake_socket)
        self.assertIsNone(fake_socket.timeout)
        connection.close()

    def test_websocket_timeout_is_reported_as_connection_close(self) -> None:
        fake_socket = _FakeSocket(raise_timeout=True)
        connection = WebSocketConnection(fake_socket)
        with self.assertRaises(ConnectionError):
            connection.recv_text()
        connection.close()

    def test_live_run_manager_streams_prompt_and_accepts_input(self) -> None:
        if os.name == "nt" and importlib.util.find_spec("winpty") is None:
            self.skipTest("pywinpty ist fuer Windows-PTY-Tests nicht installiert")
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            repository = SchoolRepository(config.database_path)
            repository.put_setting("runner_backend", "process")
            repository.put_setting("unsafe_process_backend_enabled", True)
            workspace = WorkspaceManager(config)
            runner = CodeRunner(config, _FakeToolSandbox(), workspace, repository)
            manager = LiveRunManager(runner, repository)

            try:
                project = {
                    "project_id": "proj-live",
                    "owner_type": "user",
                    "owner_key": "student",
                    "slug": "live-python",
                    "template": "python",
                    "runtime": "python",
                    "main_file": "main.py",
                    "name": "Live Python",
                }
                workspace.materialize_project(project)
                connection = _RecordingConnection()
                client = RealtimeClient("client-1", connection, _TeacherSession(), project)

                manager.start(
                    client,
                    {
                        "path": "main.py",
                        "language": "python",
                        "code": "name = input('Name: ')\nprint(f'Hallo {name}!')\n",
                        "client_meta": {"target_kind": "cell", "cell_id": "cell-1"},
                        "terminal": {"pty": True, "cols": 96, "rows": 28},
                    },
                )

                deadline = time.time() + 5
                session_id = ""
                while time.time() < deadline:
                    events = connection.snapshot()
                    started = next((event for event in events if event.get("type") == "run.started"), None)
                    if started:
                        session_id = str(started["session_id"])
                        break
                    time.sleep(0.05)
                self.assertTrue(session_id)
                manager.resize(_TeacherSession(), session_id, 100, 32)

                manager.send_input(_TeacherSession(), session_id, "Nova\n")

                deadline = time.time() + 5
                while time.time() < deadline:
                    events = connection.snapshot()
                    if any(event.get("type") == "run.exit" for event in events):
                        break
                    time.sleep(0.05)

                events = connection.snapshot()
                output = "".join(str(event.get("chunk", "")) for event in events if event.get("type") == "run.output")
                exit_event = next(event for event in events if event.get("type") == "run.exit")
                started_event = next(event for event in events if event.get("type") == "run.started")
                self.assertIn("Name:", output)
                self.assertIn("Hallo Nova!", output)
                self.assertEqual(exit_event["returncode"], 0)
                self.assertEqual(started_event["client_meta"]["cell_id"], "cell-1")
                self.assertEqual(exit_event["client_meta"]["target_kind"], "cell")
                self.assertTrue(started_event["terminal"]["requested"])
            finally:
                manager.close()
                repository.close()


if __name__ == "__main__":
    unittest.main()

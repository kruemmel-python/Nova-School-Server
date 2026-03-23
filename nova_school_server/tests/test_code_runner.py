from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from nova_school_server.code_runner import CodeRunner, RunResult, _RawResult
from nova_school_server.config import ServerConfig
from nova_school_server.workspace import WorkspaceManager


class _FakeToolSandbox:
    def authorize(self, *_args, **_kwargs):  # pragma: no cover
        return {}


class _FakeRepository:
    def __init__(self, settings: dict[str, str]) -> None:
        self.settings = settings

    def get_setting(self, key: str, default=None):
        return self.settings.get(key, default)


class _ObservedCodeRunner(CodeRunner):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.last_command: list[str] | None = None
        self.last_env: dict[str, str] | None = None

    def _execute(self, run_id, language, command, cwd, stdin_text, env, tool_session, permissions):
        self.last_command = command
        self.last_env = dict(env)
        return RunResult(run_id=run_id, language=language, command=command)


class _ContainerObservedRunner(CodeRunner):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.raw_commands: list[list[str]] = []
        self.last_container_command: list[str] | None = None
        self.last_container_env: dict[str, str] | None = None

    def _execute_raw(self, command, cwd, stdin_text, env, *, timeout_seconds=None):
        self.raw_commands.append(list(command))
        command_text = " ".join(command)
        if "pip install" in command_text:
            deps_root = Path(cwd) / ".nova-python" / "site-packages"
            deps_root.mkdir(parents=True, exist_ok=True)
            (deps_root / "demo.py").write_text("value = 1\n", encoding="utf-8")
        return _RawResult("", "", 0, 1, list(command))

    def _execute_container(self, run_id, language, runtime_executable, image, inner_command, project_root, container_workspace, stdin_text, env, tool_session, permissions):
        self.last_container_command = list(inner_command)
        self.last_container_env = dict(env)
        if "python_gui_snapshot.sh" in " ".join(inner_command):
            preview = Path(container_workspace) / ".nova-build" / "gui-preview.png"
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview.write_bytes(b"PNG")
        return RunResult(run_id=run_id, language=language, command=list(inner_command), stdout="", stderr="", notes=self._backend_notes(permissions, "container", runtime_executable, image))


class _Session:
    username = "student"
    role = "student"
    is_teacher = False
    permissions = {
        "run.python": True,
        "run.html": True,
        "web.access": False,
    }


class _TeacherSession(_Session):
    username = "teacher"
    role = "teacher"
    is_teacher = True


class CodeRunnerTests(unittest.TestCase):
    def test_runner_backend_uses_valid_repository_setting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({"runner_backend": "container"}))
            self.assertEqual(runner._runner_backend({}), "container")

    def test_runner_backend_falls_back_for_invalid_repository_setting(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({"runner_backend": "blob"}))
            self.assertEqual(runner._runner_backend({}), "container")

    def test_process_backend_requires_explicit_unsafe_enablement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(
                config,
                _FakeToolSandbox(),
                WorkspaceManager(config),
                _FakeRepository({"runner_backend": "process", "unsafe_process_backend_enabled": False}),
            )
            with self.assertRaises(PermissionError):
                runner.resolve_backend(_Session(), {"runner_backend": "process"}, purpose="Test")

    def test_html_preview_bypasses_process_backend_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(
                config,
                _FakeToolSandbox(),
                WorkspaceManager(config),
                _FakeRepository({"runner_backend": "process", "unsafe_process_backend_enabled": False}),
            )
            project = {
                "project_id": "proj-html",
                "owner_type": "user",
                "owner_key": "student",
                "slug": "html-labor",
                "template": "frontend-lab",
                "runtime": "html",
                "main_file": "index.html",
            }

            result = runner.run(
                _Session(),
                project,
                {
                    "path": "index.html",
                    "language": "html",
                    "code": "<h1>Preview</h1>",
                },
            )

            self.assertEqual(result["returncode"], 0)
            self.assertEqual(result["command"], ["preview"])
            self.assertTrue(result["preview_path"])

    def test_scheduler_serializes_same_student_user(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(
                config,
                _FakeToolSandbox(),
                WorkspaceManager(config),
                _FakeRepository({"scheduler_max_concurrent_global": 2, "scheduler_max_concurrent_student": 1}),
            )
            lease_one = runner.scheduler.acquire("student", "student")
            acquired: list[object] = []

            def worker() -> None:
                acquired.append(runner.scheduler.acquire("student", "student"))

            thread = threading.Thread(target=worker)
            thread.start()
            time.sleep(0.15)
            self.assertEqual(len(acquired), 0)
            runner.scheduler.release(lease_one)
            thread.join(timeout=2)
            self.assertEqual(len(acquired), 1)
            runner.scheduler.release(acquired[0])

    def test_container_base_command_disables_network_without_web_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({}))
            command = runner._container_base_command("docker", "python:3.12-slim", Path(tmp), Path(tmp) / "container-workspace", {"web.access": False})
            self.assertIn("none", command)
            self.assertNotIn("bridge", command)
            self.assertIn("--read-only", command)
            if os.name == "nt":
                self.assertNotIn("seccomp=", " ".join(command))
            else:
                self.assertIn("seccomp=", " ".join(command))

    def test_container_base_command_enables_bridge_with_web_access(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({}))
            command = runner._container_base_command("docker", "python:3.12-slim", Path(tmp), Path(tmp) / "container-workspace", {"web.access": True})
            self.assertIn("bridge", command)

    def test_container_base_command_includes_configured_oci_runtime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({"container_oci_runtime": "runsc"}))
            command = runner._container_base_command("docker", "python:3.12-slim", Path(tmp), Path(tmp) / "container-workspace", {"web.access": False})
            self.assertIn("--runtime", command)
            self.assertIn("runsc", command)

    def test_execution_env_requires_proxy_when_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({"web_proxy_required": True}))
            with self.assertRaises(PermissionError):
                runner._execution_env(Path(tmp), web_access=True)

    def test_containerized_env_replaces_windows_host_path(self) -> None:
        env = {
            "PATH": r"C:\Windows\System32;C:\Python312",
            "SystemRoot": r"C:\Windows",
            "NOVA_SCHOOL_NETWORK": "off",
        }
        payload = CodeRunner._containerized_env(env)
        self.assertEqual(payload["PATH"], "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin")
        self.assertNotIn("SystemRoot", payload)
        self.assertEqual(payload["NOVA_SCHOOL_NETWORK"], "off")

    def test_container_runtime_error_message_explains_missing_docker_desktop_engine(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({}))
            message = runner._container_runtime_error_message(
                "docker",
                "python:3.12-slim",
                "failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.",
            )
            self.assertIn("Docker Desktop", message)
            self.assertIn("Linux-Container-Engine", message)
            self.assertIn("python:3.12-slim", message)

    def test_container_runtime_error_message_explains_internal_server_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({}))
            message = runner._container_runtime_error_message(
                "docker",
                "python:3.12-slim",
                "request returned 500 Internal Server Error for API route and version http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/_ping",
            )
            self.assertIn("500-Fehler", message)
            self.assertIn("Linux-Worker", message)
            self.assertIn("python:3.12-slim", message)

    def test_container_runtime_error_message_explains_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({}))
            message = runner._container_runtime_error_message(
                "docker",
                "python:3.12-slim",
                "Zeitlimit erreicht.",
            )
            self.assertIn("antwortet auf diesem Rechner nicht rechtzeitig", message)
            self.assertIn("Linux-Worker", message)
            self.assertIn("python:3.12-slim", message)

    def test_container_runtime_health_fails_fast_before_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = _ContainerObservedRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({}))
            project = {
                "project_id": "proj-runtime-health",
                "owner_type": "user",
                "owner_key": "student",
                "slug": "runtime-health",
                "template": "python",
                "runtime": "python",
                "main_file": "main.py",
            }
            session = type("GuiSession", (), {"username": "student", "role": "student", "is_teacher": False, "permissions": {"run.python": True, "web.access": False}})()

            def fake_execute_raw(command, cwd, stdin_text, env, *, timeout_seconds=None):
                if len(command) >= 2 and command[1] == "info":
                    return _RawResult("", "request returned 500 Internal Server Error for API route and version http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/_ping", 1, 10, list(command))
                return _RawResult("[]", "", 0, 1, list(command))

            with patch.object(runner, "_execute_raw", side_effect=fake_execute_raw):
                result = runner.run(
                    session,
                    project,
                    {
                        "path": "main.py",
                        "language": "python",
                        "code": "print('ok')\n",
                    },
                )

            self.assertEqual(result["returncode"], 2)
            self.assertIn("Docker Desktop", result["stderr"])
            self.assertIn("500-Fehler", result["stderr"])

    def test_backend_notes_omit_default_image_placeholder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({}))
            notes = runner._backend_notes({"web.access": False}, "container", "docker", "")
            self.assertTrue(notes)
            self.assertIn("Container-Isolation aktiv (docker).", notes[0])
            self.assertNotIn("default", notes[0])

    def test_python_executable_does_not_receive_py_launcher_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = _ObservedCodeRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({}))
            source = Path(tmp) / "main.py"
            source.write_text("print('ok')", encoding="utf-8")
            with patch("nova_school_server.code_runner.shutil.which", side_effect=[r"C:\Python312\python.exe"]):
                runner._run_python("run123", source, Path(tmp), "", {}, {}, {"web.access": True})
            self.assertIsNotNone(runner.last_command)
            assert runner.last_command is not None
            self.assertEqual(runner.last_command[0], r"C:\Python312\python.exe")
            self.assertNotIn("-3", runner.last_command)

    def test_run_python_supports_stdin_input(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(
                config,
                _FakeToolSandbox(),
                WorkspaceManager(config),
                _FakeRepository({"runner_backend": "process", "unsafe_process_backend_enabled": True}),
            )
            project = {
                "project_id": "proj-stdin",
                "owner_type": "user",
                "owner_key": "student",
                "slug": "stdin-labor",
                "template": "python",
                "runtime": "python",
                "main_file": "main.py",
            }

            result = runner.run(
                _TeacherSession(),
                project,
                {
                    "path": "main.py",
                    "language": "python",
                    "code": "name = input('Name: ')\nprint(f'Hallo {name}!')\n",
                    "stdin": "Nova School\n",
                },
            )

            self.assertEqual(result["returncode"], 0)
            self.assertIn("Name:", result["stdout"])
            self.assertIn("Hallo Nova School!", result["stdout"])

    def test_run_python_reports_syntax_error_before_execution(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = _ObservedCodeRunner(
                config,
                _FakeToolSandbox(),
                WorkspaceManager(config),
                _FakeRepository({"runner_backend": "process", "unsafe_process_backend_enabled": True}),
            )
            project = {
                "project_id": "proj-syntax",
                "owner_type": "user",
                "owner_key": "student",
                "slug": "syntax-labor",
                "template": "python",
                "runtime": "python",
                "main_file": "main.py",
            }

            result = runner.run(
                _TeacherSession(),
                project,
                {
                    "path": "main.py",
                    "language": "python",
                    "code": "def greet(name) -> str:\n    return name\n\ndef broken) -> str:\n    return ''\n",
                },
            )

            self.assertEqual(result["returncode"], 1)
            self.assertIn("SyntaxError", result["stderr"])
            self.assertIsNone(runner.last_command)

    def test_prepare_live_python_reports_syntax_error_before_launch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = CodeRunner(
                config,
                _FakeToolSandbox(),
                WorkspaceManager(config),
                _FakeRepository({"runner_backend": "process", "unsafe_process_backend_enabled": True}),
            )
            project = {
                "project_id": "proj-live-syntax",
                "owner_type": "user",
                "owner_key": "student",
                "slug": "live-syntax-labor",
                "template": "python",
                "runtime": "python",
                "main_file": "main.py",
            }

            prepared = runner.prepare_live_run(
                _TeacherSession(),
                project,
                {
                    "path": "main.py",
                    "language": "python",
                    "code": "def broken) -> str:\n    return ''\n",
                },
            )

            self.assertEqual(prepared.failed_returncode, 1)
            self.assertIn("SyntaxError", prepared.prelude_stderr)

    def test_run_python_uses_bootstrap_and_dependency_env_with_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = _ObservedCodeRunner(
                config,
                _FakeToolSandbox(),
                WorkspaceManager(config),
                _FakeRepository({"runner_backend": "process", "unsafe_process_backend_enabled": True}),
            )
            source = Path(tmp) / "main.py"
            source.write_text("import demo\nprint(demo.value)\n", encoding="utf-8")
            (Path(tmp) / "requirements.txt").write_text("demo-package==1.0\n", encoding="utf-8")

            def fake_execute_raw(command, cwd, stdin_text, env, *, timeout_seconds=None):
                if "-m" in command and "pip" in command:
                    deps_root = Path(cwd) / ".nova-python" / "site-packages"
                    deps_root.mkdir(parents=True, exist_ok=True)
                    (deps_root / "demo.py").write_text("value = 1\n", encoding="utf-8")
                return _RawResult("", "", 0, 1, list(command))

            with patch("nova_school_server.code_runner.shutil.which", side_effect=[r"C:\Python312\python.exe", r"C:\Python312\python.exe"]), patch.object(runner, "_execute_raw", side_effect=fake_execute_raw):
                runner._run_python("run123", source, Path(tmp), "", {}, {}, {"web.access": True})

            self.assertIsNotNone(runner.last_command)
            self.assertIsNotNone(runner.last_env)
            assert runner.last_command is not None
            assert runner.last_env is not None
            self.assertTrue(runner.last_command[-1].endswith("python_entry.py"))
            self.assertEqual(runner.last_env["NOVA_SCHOOL_ENTRYPOINT"], str(source))
            self.assertTrue(runner.last_env["NOVA_SCHOOL_PYTHON_DEPS"].endswith(str(Path(".nova-python") / "site-packages")))

    def test_containerized_python_gui_returns_preview_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = _ContainerObservedRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({}))
            project = {
                "project_id": "proj-gui",
                "owner_type": "user",
                "owner_key": "student",
                "slug": "gui-labor",
                "template": "python",
                "runtime": "python",
                "main_file": "main.py",
            }
            session = type("GuiSession", (), {"username": "student", "role": "student", "is_teacher": False, "permissions": {"run.python": True, "web.access": True}})()

            result = runner.run(
                session,
                project,
                {
                    "path": "main.py",
                    "language": "python",
                    "code": "import tkinter as tk\nroot = tk.Tk()\nroot.mainloop()\n",
                },
            )

            self.assertEqual(result["returncode"], 0)
            self.assertTrue(result["preview_path"].endswith("/gui-preview.png"))
            self.assertIsNotNone(runner.last_container_command)
            assert runner.last_container_command is not None
            self.assertIn("python_gui_snapshot.sh", " ".join(runner.last_container_command))
            self.assertIn("GUI-Snapshot-Modus aktiv", "\n".join(result["notes"]))

    def test_containerized_python_mainloop_without_direct_import_uses_gui_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config = ServerConfig.from_base_path(Path(tmp))
            runner = _ContainerObservedRunner(config, _FakeToolSandbox(), WorkspaceManager(config), _FakeRepository({}))
            project = {
                "project_id": "proj-mainloop",
                "owner_type": "user",
                "owner_key": "student",
                "slug": "mainloop-labor",
                "template": "python",
                "runtime": "python",
                "main_file": "main.py",
            }
            session = type("GuiSession", (), {"username": "student", "role": "student", "is_teacher": False, "permissions": {"run.python": True, "web.access": True}})()

            result = runner.run(
                session,
                project,
                {
                    "path": "main.py",
                    "language": "python",
                    "code": "from appkit import build_view\nview = build_view()\nview.mainloop()\n",
                },
            )

            self.assertEqual(result["returncode"], 0)
            self.assertTrue(result["preview_path"].endswith("/gui-preview.png"))
            self.assertIsNotNone(runner.last_container_command)
            assert runner.last_container_command is not None
            self.assertIn("python_gui_snapshot.sh", " ".join(runner.last_container_command))


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import os
import re
import shlex
import shutil
import subprocess
import threading
import time
import textwrap
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import ServerConfig
from .container_seccomp import resolve_seccomp_profile_option
from .permissions import allowed_tool_names
from .workspace import WorkspaceManager


LANGUAGE_TO_PERMISSION = {
    "python": "run.python",
    "javascript": "run.javascript",
    "cpp": "run.cpp",
    "java": "run.java",
    "rust": "run.rust",
    "html": "run.html",
    "node": "run.node",
    "npm": "run.npm",
}

EXTENSION_TO_LANGUAGE = {
    ".py": "python",
    ".js": "javascript",
    ".cjs": "javascript",
    ".mjs": "javascript",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".java": "java",
    ".rs": "rust",
    ".html": "html",
    ".htm": "html",
}

DEFAULT_CONTAINER_IMAGES = {
    "python": "python:3.12-slim",
    "node": "node:20-bookworm-slim",
    "cpp": "gcc:14",
    "java": "eclipse-temurin:21",
    "rust": "rust:1.81",
}

_PYTHON_GUI_IMPORT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("tkinter", re.compile(r"^\s*import\s+tkinter\b", re.IGNORECASE | re.MULTILINE)),
    ("tkinter", re.compile(r"^\s*from\s+tkinter\b", re.IGNORECASE | re.MULTILINE)),
    ("customtkinter", re.compile(r"^\s*import\s+customtkinter\b", re.IGNORECASE | re.MULTILINE)),
    ("customtkinter", re.compile(r"^\s*from\s+customtkinter\b", re.IGNORECASE | re.MULTILINE)),
    ("turtle", re.compile(r"^\s*import\s+turtle\b", re.IGNORECASE | re.MULTILINE)),
    ("turtle", re.compile(r"^\s*from\s+turtle\b", re.IGNORECASE | re.MULTILINE)),
    ("PyQt", re.compile(r"^\s*import\s+PyQt\d*\b", re.IGNORECASE | re.MULTILINE)),
    ("PyQt", re.compile(r"^\s*from\s+PyQt\d*\b", re.IGNORECASE | re.MULTILINE)),
    ("PySide", re.compile(r"^\s*import\s+PySide\d*\b", re.IGNORECASE | re.MULTILINE)),
    ("PySide", re.compile(r"^\s*from\s+PySide\d*\b", re.IGNORECASE | re.MULTILINE)),
    ("wx", re.compile(r"^\s*import\s+wx\b", re.IGNORECASE | re.MULTILINE)),
    ("wx", re.compile(r"^\s*from\s+wx\b", re.IGNORECASE | re.MULTILINE)),
)

_PYTHON_GUI_USAGE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("desktop-gui", re.compile(r"\.\s*mainloop\s*\(", re.IGNORECASE)),
    ("desktop-gui", re.compile(r"\bmainloop\s*\(", re.IGNORECASE)),
    ("tkinter", re.compile(r"\bTk\s*\(", re.IGNORECASE)),
    ("tkinter", re.compile(r"\bToplevel\s*\(", re.IGNORECASE)),
    ("PyQt", re.compile(r"\bQApplication\s*\(", re.IGNORECASE)),
    ("PySide", re.compile(r"\bQApplication\s*\(", re.IGNORECASE)),
    ("wx", re.compile(r"\bwx\.App\s*\(", re.IGNORECASE)),
)


@dataclass(slots=True)
class RunResult:
    run_id: str
    language: str
    command: list[str]
    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    duration_ms: int = 0
    preview_path: str = ""
    notes: list[str] | None = None
    tool_session: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "language": self.language,
            "command": self.command,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
            "duration_ms": self.duration_ms,
            "preview_path": self.preview_path,
            "notes": self.notes or [],
            "tool_session": self.tool_session or {},
        }


@dataclass(slots=True)
class LivePreparedRun:
    session_id: str
    run_id: str
    language: str
    command: list[str]
    cwd: Path
    env: dict[str, str]
    notes: list[str]
    tool_session: dict[str, Any]
    pty_command: list[str] | None = None
    preview_path: str = ""
    prelude_stdout: str = ""
    prelude_stderr: str = ""
    failed_returncode: int | None = None
    scheduler_lease: "SchedulerLease | None" = None


@dataclass(slots=True)
class SchedulerLease:
    lease_id: str
    owner_username: str
    role: str
    priority: int
    waited_ms: int
    queue_position: int


class RunScheduler:
    def __init__(self, repository: Any | None = None) -> None:
        self.repository = repository
        self._condition = threading.Condition()
        self._queue: list[dict[str, Any]] = []
        self._active_total = 0
        self._active_by_owner: dict[str, int] = {}
        self._sequence = 0

    def acquire(self, owner_username: str, role: str) -> SchedulerLease:
        request = {
            "request_id": uuid.uuid4().hex[:12],
            "owner_username": owner_username,
            "role": role,
            "priority": self._priority_for_role(role),
            "submitted_at": time.perf_counter(),
        }
        with self._condition:
            self._sequence += 1
            request["sequence"] = self._sequence
            self._queue.append(request)
            first_position = 1
            while True:
                ordered = sorted(self._queue, key=lambda item: (int(item["priority"]), int(item["sequence"])))
                current = next((index + 1 for index, item in enumerate(ordered) if item["request_id"] == request["request_id"]), len(ordered))
                first_position = min(first_position, current)
                if ordered and ordered[0]["request_id"] == request["request_id"] and self._can_activate(owner_username, role):
                    self._queue = [item for item in self._queue if item["request_id"] != request["request_id"]]
                    self._active_total += 1
                    self._active_by_owner[owner_username] = self._active_by_owner.get(owner_username, 0) + 1
                    return SchedulerLease(
                        lease_id=str(request["request_id"]),
                        owner_username=owner_username,
                        role=role,
                        priority=int(request["priority"]),
                        waited_ms=int((time.perf_counter() - float(request["submitted_at"])) * 1000),
                        queue_position=first_position,
                    )
                self._condition.wait(timeout=0.1)

    def release(self, lease: SchedulerLease | None) -> None:
        if lease is None:
            return
        with self._condition:
            self._active_total = max(0, self._active_total - 1)
            current = max(0, self._active_by_owner.get(lease.owner_username, 0) - 1)
            if current <= 0:
                self._active_by_owner.pop(lease.owner_username, None)
            else:
                self._active_by_owner[lease.owner_username] = current
            self._condition.notify_all()

    def _can_activate(self, owner_username: str, role: str) -> bool:
        return self._active_total < self._global_limit() and self._active_by_owner.get(owner_username, 0) < self._per_owner_limit(role)

    def _global_limit(self) -> int:
        return self._setting_int("scheduler_max_concurrent_global", 4, minimum=1)

    def _per_owner_limit(self, role: str) -> int:
        key = {
            "student": "scheduler_max_concurrent_student",
            "teacher": "scheduler_max_concurrent_teacher",
            "admin": "scheduler_max_concurrent_admin",
        }.get(role, "scheduler_max_concurrent_student")
        default = {"student": 1, "teacher": 2, "admin": 3}.get(role, 1)
        return self._setting_int(key, default, minimum=1)

    def _setting_int(self, key: str, default: int, *, minimum: int = 1) -> int:
        if self.repository is None:
            return default
        try:
            value = int(self.repository.get_setting(key, default))
        except Exception:
            return default
        return max(minimum, value)

    @staticmethod
    def _priority_for_role(role: str) -> int:
        return {"admin": 0, "teacher": 1, "student": 2}.get(role, 2)


class CodeRunner:
    def __init__(self, config: ServerConfig, tool_sandbox: Any, workspace_manager: WorkspaceManager, repository: Any | None = None) -> None:
        self.config = config
        self.tool_sandbox = tool_sandbox
        self.workspace_manager = workspace_manager
        self.repository = repository
        self.scheduler = RunScheduler(repository)
        self._container_runtime_health_cache: dict[str, tuple[float, bool, str]] = {}

    def run(self, session: Any, project: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        run_id = uuid.uuid4().hex[:10]
        language = self._resolve_language(project, payload)
        backend = self._runner_backend(payload) if language == "html" else self.resolve_backend(session, payload, purpose="Projektlauf")
        permission_key = LANGUAGE_TO_PERMISSION.get(language)
        if permission_key is None or not session.permissions.get(permission_key, False):
            raise PermissionError(f"Ausfuehrung fuer {language} ist nicht freigegeben.")

        tool_session = self.tool_sandbox.authorize(
            f"user:{session.username}",
            allowed_tools=allowed_tool_names(session.permissions),
            requested_tools={permission_key},
            metadata={"project_id": project["project_id"], "language": language, "backend": backend},
        )

        project_root = self.workspace_manager.project_root(project)
        run_root = project_root / ".nova-school" / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)

        if language == "html":
            source_path = self._prepare_source_file(project, payload, language, run_root)
            preview_target = self._prepare_html_preview(project, payload, source_path, project_root)
            return RunResult(
                run_id=run_id,
                language=language,
                command=["preview"],
                stdout="HTML-Vorschau aktualisiert.\n",
                preview_path=preview_target,
                tool_session=tool_session,
                notes=self._backend_notes(session.permissions, backend),
            ).to_dict()

        execution_root, source_path = self._prepare_execution_workspace(project, payload, language, project_root, run_root)
        if language == "python":
            syntax_error = self._python_syntax_error(source_path, display_path=Path(payload.get("path") or project.get("main_file") or source_path.name).as_posix())
            if syntax_error:
                return RunResult(
                    run_id=run_id,
                    language=language,
                    command=["python", "-m", "py_compile", Path(payload.get("path") or project.get("main_file") or source_path.name).as_posix()],
                    stderr=syntax_error,
                    returncode=1,
                    notes=self._backend_notes(session.permissions, backend),
                    tool_session=tool_session,
                ).to_dict()
        stdin_text = str(payload.get("stdin") or "")
        env = self._execution_env(execution_root, web_access=bool(session.permissions.get("web.access", False)))
        lease = self.scheduler.acquire(session.username, self._session_role(session))
        try:
            if backend == "container":
                result = self._run_containerized(run_id, language, source_path, run_root, execution_root, stdin_text, env, tool_session, session.permissions, payload)
            elif language == "python":
                result = self._run_python(run_id, source_path, execution_root, stdin_text, env, tool_session, session.permissions)
            elif language in {"javascript", "node"}:
                result = self._run_node_like(run_id, language, source_path, execution_root, stdin_text, env, tool_session, session.permissions)
            elif language == "cpp":
                result = self._run_cpp(run_id, source_path, run_root, execution_root, stdin_text, env, tool_session, session.permissions)
            elif language == "java":
                result = self._run_java(run_id, source_path, run_root, execution_root, stdin_text, env, tool_session, session.permissions)
            elif language == "rust":
                result = self._run_rust(run_id, source_path, run_root, execution_root, stdin_text, env, tool_session, session.permissions)
            elif language == "npm":
                result = self._run_npm(run_id, execution_root, payload, stdin_text, env, tool_session, session.permissions)
            else:
                raise ValueError(f"unsupported language: {language}")
        finally:
            self.scheduler.release(lease)
        notes = list(result.notes or [])
        notes.extend(self._scheduler_notes(lease))
        result.notes = notes
        return result.to_dict()

    def prepare_live_run(self, session: Any, project: dict[str, Any], payload: dict[str, Any]) -> LivePreparedRun:
        run_id = uuid.uuid4().hex[:10]
        session_id = uuid.uuid4().hex[:12]
        language = self._resolve_language(project, payload)
        backend = self._runner_backend(payload) if language == "html" else self.resolve_backend(session, payload, purpose="Live-Lauf")
        permission_key = LANGUAGE_TO_PERMISSION.get(language)
        if permission_key is None or not session.permissions.get(permission_key, False):
            raise PermissionError(f"Ausfuehrung fuer {language} ist nicht freigegeben.")

        tool_session = self.tool_sandbox.authorize(
            f"user:{session.username}",
            allowed_tools=allowed_tool_names(session.permissions),
            requested_tools={permission_key},
            metadata={"project_id": project["project_id"], "language": language, "backend": backend, "mode": "live"},
        )

        project_root = self.workspace_manager.project_root(project)
        run_root = project_root / ".nova-school" / "runs" / run_id
        run_root.mkdir(parents=True, exist_ok=True)

        if language == "html":
            source_path = self._prepare_source_file(project, payload, language, run_root)
            notes = self._backend_notes(session.permissions, backend)
            preview_target = self._prepare_html_preview(project, payload, source_path, project_root)
            env = self._execution_env(project_root, web_access=bool(session.permissions.get("web.access", False)))
            return LivePreparedRun(
                session_id=session_id,
                run_id=run_id,
                language=language,
                command=["preview"],
                cwd=project_root,
                env=env,
                notes=notes,
                tool_session=tool_session,
                preview_path=preview_target,
                prelude_stdout="HTML-Vorschau aktualisiert.\n",
                failed_returncode=0,
            )

        execution_root, source_path = self._prepare_execution_workspace(project, payload, language, project_root, run_root)
        if language == "python":
            syntax_error = self._python_syntax_error(source_path, display_path=Path(payload.get("path") or project.get("main_file") or source_path.name).as_posix())
            if syntax_error:
                return LivePreparedRun(
                    session_id=session_id,
                    run_id=run_id,
                    language=language,
                    command=["python", "-m", "py_compile", Path(payload.get("path") or project.get("main_file") or source_path.name).as_posix()],
                    cwd=project_root,
                    env={},
                    notes=self._backend_notes(session.permissions, backend),
                    tool_session=tool_session,
                    prelude_stderr=syntax_error,
                    failed_returncode=1,
                )
        env = self._execution_env(execution_root, web_access=bool(session.permissions.get("web.access", False)))
        lease = self.scheduler.acquire(session.username, self._session_role(session))
        notes = self._backend_notes(session.permissions, backend) + self._scheduler_notes(lease)
        try:
            if backend == "container":
                prepared = self._prepare_live_containerized(session_id, run_id, language, source_path, run_root, execution_root, env, tool_session, session.permissions, payload)
            else:
                prepared = self._prepare_live_process(session_id, run_id, language, source_path, run_root, execution_root, env, tool_session, session.permissions, payload)
        except Exception:
            self.scheduler.release(lease)
            raise
        prepared.notes = list(prepared.notes or []) + self._scheduler_notes(lease)
        prepared.scheduler_lease = lease
        return prepared

    def _resolve_language(self, project: dict[str, Any], payload: dict[str, Any]) -> str:
        explicit = str(payload.get("language") or "").strip().lower()
        if explicit:
            return explicit
        path_text = str(payload.get("path") or project.get("main_file") or "")
        return EXTENSION_TO_LANGUAGE.get(Path(path_text).suffix.lower(), str(project.get("runtime") or "python"))

    def _prepare_source_file(self, project: dict[str, Any], payload: dict[str, Any], language: str, run_root: Path) -> Path:
        code = payload.get("code")
        path_text = str(payload.get("path") or project.get("main_file") or "").strip()
        if code is not None:
            target = run_root / Path(path_text or self._default_filename(language)).name
            target.write_text(str(code), encoding="utf-8")
            return target
        if not path_text:
            raise FileNotFoundError("keine Datei zum Ausfuehren angegeben")
        return self.workspace_manager.resolve_project_path(project, path_text)

    def _prepare_execution_workspace(self, project: dict[str, Any], payload: dict[str, Any], language: str, project_root: Path, run_root: Path) -> tuple[Path, Path]:
        runtime_root = run_root / "workspace"
        self._copy_project_tree(project_root, runtime_root)
        path_text = str(payload.get("path") or project.get("main_file") or "").strip()
        relative_target = self._safe_relative_path(path_text or self._default_filename(language))
        source_path = runtime_root / relative_target
        if payload.get("code") is not None:
            source_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.write_text(str(payload.get("code") or ""), encoding="utf-8")
        elif not source_path.exists():
            raise FileNotFoundError(f"Datei fuer die isolierte Ausfuehrung nicht gefunden: {relative_target.as_posix()}")
        (runtime_root / ".nova-build").mkdir(parents=True, exist_ok=True)
        (runtime_root / ".nova-cache").mkdir(parents=True, exist_ok=True)
        (runtime_root / ".nova-tmp").mkdir(parents=True, exist_ok=True)
        return runtime_root, source_path

    def _copy_project_tree(self, project_root: Path, runtime_root: Path) -> None:
        ignored_names = {"__pycache__", ".git", ".venv", "venv", "node_modules", "dist", "build", "target", ".nova-school"}
        self._mirror_tree_securely(project_root, runtime_root, ignored_names)

    @staticmethod
    def _safe_relative_path(path_text: str) -> Path:
        candidate = Path(path_text.replace("\\", "/"))
        if candidate.is_absolute() or ".." in candidate.parts:
            raise PermissionError("Ungueltiger Projektpfad fuer die Ausfuehrung.")
        parts = [part for part in candidate.parts if part not in {"", "."}]
        if not parts:
            raise PermissionError("Leerer Projektpfad fuer die Ausfuehrung.")
        return Path(*parts)

    def _prepare_html_preview(self, project: dict[str, Any], payload: dict[str, Any], source_path: Path, project_root: Path) -> str:
        if payload.get("code") is not None:
            preview_file = project_root / ".nova-school" / "live-preview.html"
            preview_file.parent.mkdir(parents=True, exist_ok=True)
            preview_file.write_text(str(payload.get("code") or ""), encoding="utf-8")
            return preview_file.relative_to(project_root).as_posix()
        return source_path.relative_to(project_root).as_posix()

    def _detect_python_gui_frameworks(self, language: str, source_path: Path, payload: dict[str, Any]) -> list[str]:
        if language != "python":
            return []
        source_text = str(payload.get("code") or "") if payload.get("code") is not None else self._read_source_text(source_path)
        if not source_text:
            return []
        frameworks: list[str] = []
        for label, pattern in _PYTHON_GUI_IMPORT_PATTERNS:
            if pattern.search(source_text) and label not in frameworks:
                frameworks.append(label)
        for label, pattern in _PYTHON_GUI_USAGE_PATTERNS:
            if pattern.search(source_text) and label not in frameworks:
                frameworks.append(label)
        return frameworks

    @staticmethod
    def _read_source_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except Exception:
            try:
                return path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                return ""

    def _python_syntax_error(self, source_path: Path, *, display_path: str | None = None) -> str:
        source_text = self._read_source_text(source_path)
        if not source_text:
            return ""
        try:
            compile(source_text, str(display_path or source_path), "exec")
        except SyntaxError as exc:
            line_text = str((exc.text or "").rstrip("\n"))
            caret = ""
            if line_text and exc.offset:
                caret = " " * max(int(exc.offset) - 1, 0) + "^"
            parts = [f'  File "{display_path or source_path.as_posix()}", line {int(exc.lineno or 1)}']
            if line_text:
                parts.append(f"    {line_text}")
                if caret:
                    parts.append(f"    {caret}")
            parts.append(f"SyntaxError: {exc.msg}")
            return "\n".join(parts) + "\n"
        return ""

    @staticmethod
    def _python_requirements_file(workspace_root: Path) -> Path | None:
        requirements_path = workspace_root / "requirements.txt"
        if not requirements_path.exists() or not requirements_path.is_file():
            return None
        try:
            content = requirements_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        if not any(line.strip() and not line.strip().startswith("#") for line in content.splitlines()):
            return None
        return requirements_path

    def _python_dependency_cache_dir(self, requirements_path: Path, backend_marker: str) -> Path:
        digest = hashlib.sha256()
        digest.update(backend_marker.encode("utf-8"))
        digest.update(b"\n")
        digest.update(requirements_path.read_bytes())
        return self.config.data_path / "python_package_cache" / digest.hexdigest()[:16]

    @staticmethod
    def _restore_dependency_cache(target_root: Path, cache_root: Path) -> bool:
        if not cache_root.exists():
            return False
        if target_root.exists():
            shutil.rmtree(target_root, ignore_errors=True)
        shutil.copytree(cache_root, target_root, dirs_exist_ok=True)
        return True

    @staticmethod
    def _store_dependency_cache(source_root: Path, cache_root: Path) -> None:
        if not source_root.exists():
            return
        if cache_root.exists():
            shutil.rmtree(cache_root, ignore_errors=True)
        cache_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_root, cache_root, dirs_exist_ok=True)

    def _write_python_bootstrap(self, workspace_root: Path) -> Path:
        bootstrap_path = workspace_root / ".nova-build" / "python_entry.py"
        bootstrap_path.parent.mkdir(parents=True, exist_ok=True)
        bootstrap_path.write_text(
            textwrap.dedent(
                """\
                from __future__ import annotations

                import os
                import runpy
                import sys
                from pathlib import Path

                entrypoint = os.environ.get("NOVA_SCHOOL_ENTRYPOINT", "").strip()
                deps_path = os.environ.get("NOVA_SCHOOL_PYTHON_DEPS", "").strip()

                if not entrypoint:
                    raise SystemExit("NOVA_SCHOOL_ENTRYPOINT fehlt.")

                if deps_path:
                    deps_dir = Path(deps_path)
                    if deps_dir.exists():
                        sys.path.insert(0, str(deps_dir))

                entry = Path(entrypoint)
                if entry.parent.exists():
                    sys.path.insert(0, str(entry.parent))
                    os.chdir(entry.parent)

                sys.argv = [str(entry), *sys.argv[1:]]
                runpy.run_path(str(entry), run_name="__main__")
                """
            ),
            encoding="utf-8",
        )
        return bootstrap_path

    def _python_entry_env(self, env: dict[str, str], entrypoint_path: str, deps_path: str | None) -> dict[str, str]:
        prepared = dict(env)
        prepared["NOVA_SCHOOL_ENTRYPOINT"] = entrypoint_path
        if deps_path:
            prepared["NOVA_SCHOOL_PYTHON_DEPS"] = deps_path
        else:
            prepared.pop("NOVA_SCHOOL_PYTHON_DEPS", None)
        return prepared

    def _run_containerized(
        self,
        run_id: str,
        language: str,
        source_path: Path,
        run_root: Path,
        project_root: Path,
        stdin_text: str,
        env: dict[str, str],
        tool_session: dict[str, Any],
        permissions: dict[str, bool],
        payload: dict[str, Any],
    ) -> RunResult:
        runtime = self._container_runtime(payload)
        runtime_executable = shutil.which(runtime) or runtime
        image = self._container_image(language, payload)
        healthy, runtime_error = self._container_runtime_health(runtime_executable, image)
        if not healthy:
            return RunResult(run_id, language, [runtime_executable, "info"], "", runtime_error, 2, notes=self._backend_notes(permissions, "container", runtime, image), tool_session=tool_session)
        container_workspace = self._prepare_container_workspace(project_root, run_root)
        container_source_path = container_workspace / source_path.relative_to(project_root)
        extra_notes: list[str] = []
        inspect_command = [runtime_executable, "image", "inspect", image]
        inspect_result = self._execute_raw(inspect_command, project_root, "", dict(os.environ))
        if inspect_result.returncode != 0:
            stderr = self._container_runtime_error_message(runtime_executable, image, inspect_result.stderr)
            return RunResult(run_id, language, inspect_command, inspect_result.stdout, stderr, inspect_result.returncode, inspect_result.duration_ms, notes=self._backend_notes(permissions, "container", runtime, image), tool_session=tool_session)

        if language == "python":
            gui_frameworks = self._detect_python_gui_frameworks(language, source_path, payload)
            deps_root, dependency_notes, dependency_error = self._ensure_python_dependencies_container(runtime_executable, image, container_workspace, env, permissions)
            if dependency_error:
                return RunResult(run_id, language, ["pip", "install"], "", dependency_error, 2, notes=self._backend_notes(permissions, "container", runtime, image), tool_session=tool_session)
            extra_notes.extend(dependency_notes)
            bootstrap_path = self._write_python_bootstrap(container_workspace)
            container_env = self._python_entry_env(
                self._containerized_env(env),
                self._container_path(container_workspace, container_source_path),
                self._container_path(container_workspace, deps_root) if deps_root else None,
            )
            preview_path = ""
            if gui_frameworks:
                image, gui_notes, gui_error = self._ensure_python_gui_container_image(runtime_executable, image, permissions)
                if gui_error:
                    return RunResult(run_id, language, ["docker", "build"], "", gui_error, 2, notes=self._backend_notes(permissions, "container", runtime, image), tool_session=tool_session)
                extra_notes.extend(gui_notes)
                extra_notes.append(
                    "GUI-Snapshot-Modus aktiv: Python-GUI-Programme werden fuer die Browser-Oberflaeche kurz in einer virtuellen Anzeige gestartet und als Vorschau gespeichert."
                )
                snapshot_script, _live_script = self._prepare_python_gui_scripts(container_workspace, container_source_path)
                inner_command = ["/bin/sh", self._container_path(container_workspace, snapshot_script)]
                preview_path = f".nova-school/runs/{run_id}/container-workspace/.nova-build/gui-preview.png"
            else:
                inner_command = ["python", "-I", self._container_path(container_workspace, bootstrap_path)]
            result = self._execute_container(
                run_id,
                language,
                runtime_executable,
                image,
                inner_command,
                container_workspace,
                container_workspace,
                stdin_text,
                container_env,
                tool_session,
                permissions,
            )
            result.notes = list(result.notes or []) + extra_notes
            if preview_path and (run_root / "container-workspace" / ".nova-build" / "gui-preview.png").exists():
                result.preview_path = preview_path
            elif gui_frameworks:
                result.notes.append(
                    "Python-GUI erkannt. Fuer ein sichtbares Browser-Fenster wird derzeit ein GUI-Snapshot erzeugt; interaktive Desktop-Fenster werden noch nicht live gespiegelt."
                )
            return result
        if language in {"javascript", "node"}:
            inner_command = ["node", self._container_path(project_root, source_path)]
            return self._execute_container(run_id, language, runtime_executable, image, inner_command, project_root, container_workspace, stdin_text, env, tool_session, permissions)
        if language == "cpp":
            container_source = self._container_path(project_root, source_path)
            build_root = project_root / ".nova-build"
            build_root.mkdir(parents=True, exist_ok=True)
            container_binary = self._container_path(project_root, build_root / ("program.exe" if os.name == "nt" else "program"))
            compile = self._execute_container_raw(runtime_executable, image, ["g++", "-std=c++20", "-O2", container_source, "-o", container_binary], project_root, container_workspace, "", env, permissions)
            if compile.returncode != 0:
                return RunResult(run_id, language, compile.command, compile.stdout, compile.stderr, compile.returncode, compile.duration_ms, notes=self._backend_notes(permissions, "container", runtime, image), tool_session=tool_session)
            run_result = self._execute_container(run_id, language, runtime_executable, image, [container_binary], project_root, container_workspace, stdin_text, env, tool_session, permissions)
            run_result.stdout = (compile.stdout + run_result.stdout).strip() + ("\n" if (compile.stdout or run_result.stdout) else "")
            return run_result
        if language == "java":
            container_source = self._container_path(project_root, source_path)
            build_root = project_root / ".nova-build"
            build_root.mkdir(parents=True, exist_ok=True)
            container_output = self._container_path(project_root, build_root)
            compile = self._execute_container_raw(runtime_executable, image, ["javac", "-d", container_output, container_source], project_root, container_workspace, "", env, permissions)
            if compile.returncode != 0:
                return RunResult(run_id, language, compile.command, compile.stdout, compile.stderr, compile.returncode, compile.duration_ms, notes=self._backend_notes(permissions, "container", runtime, image), tool_session=tool_session)
            run_result = self._execute_container(run_id, language, runtime_executable, image, ["java", "-cp", container_output, source_path.stem], project_root, container_workspace, stdin_text, env, tool_session, permissions)
            run_result.stdout = (compile.stdout + run_result.stdout).strip() + ("\n" if (compile.stdout or run_result.stdout) else "")
            return run_result
        if language == "rust":
            cargo_manifest = project_root / "Cargo.toml"
            if cargo_manifest.exists():
                manifest_path = self._container_path(project_root, cargo_manifest)
                return self._execute_container(run_id, language, runtime_executable, image, ["cargo", "run", "--manifest-path", manifest_path], project_root, container_workspace, stdin_text, env, tool_session, permissions)
            container_source = self._container_path(project_root, source_path)
            build_root = project_root / ".nova-build"
            build_root.mkdir(parents=True, exist_ok=True)
            container_binary = self._container_path(project_root, build_root / ("program.exe" if os.name == "nt" else "program"))
            compile = self._execute_container_raw(runtime_executable, image, ["rustc", container_source, "-o", container_binary], project_root, container_workspace, "", env, permissions)
            if compile.returncode != 0:
                return RunResult(run_id, language, compile.command, compile.stdout, compile.stderr, compile.returncode, compile.duration_ms, notes=self._backend_notes(permissions, "container", runtime, image), tool_session=tool_session)
            run_result = self._execute_container(run_id, language, runtime_executable, image, [container_binary], project_root, container_workspace, stdin_text, env, tool_session, permissions)
            run_result.stdout = (compile.stdout + run_result.stdout).strip() + ("\n" if (compile.stdout or run_result.stdout) else "")
            return run_result
        if language == "npm":
            command_text = str(payload.get("command") or "").strip()
            if not command_text:
                raise ValueError("npm benoetigt ein Kommando, z. B. `run dev` oder `install`.")
            tokens = shlex.split(command_text, posix=False)
            first = tokens[0].lower() if tokens else ""
            if first not in {"install", "run", "test", "ci", "list"}:
                raise PermissionError("Nur `install`, `run`, `test`, `ci` und `list` sind fuer npm erlaubt.")
            return self._execute_container(run_id, language, runtime_executable, image, ["npm", *tokens], project_root, container_workspace, stdin_text, env, tool_session, permissions)
        raise ValueError(f"unsupported language for container backend: {language}")

    def _run_python(self, run_id: str, source_path: Path, project_root: Path, stdin_text: str, env: dict[str, str], tool_session: dict[str, Any], permissions: dict[str, bool]) -> RunResult:
        deps_root, dependency_notes, dependency_error = self._ensure_python_dependencies_process(project_root, env, permissions)
        if dependency_error:
            return RunResult(run_id, "python", ["pip", "install"], "", dependency_error, 2, notes=self._backend_notes(permissions, "process"), tool_session=tool_session)
        executable = shutil.which("python") or shutil.which("py")
        if not executable:
            raise RuntimeError("python ist auf dem Server nicht verfuegbar")
        bootstrap_path = self._write_python_bootstrap(project_root)
        prepared_env = self._python_entry_env(env, str(source_path), str(deps_root) if deps_root else None)
        command = [executable, "-I", str(bootstrap_path)]
        if Path(executable).name.lower() in {"py", "py.exe"}:
            command = [executable, "-3", "-I", str(bootstrap_path)]
        result = self._execute(run_id, "python", command, project_root, stdin_text, prepared_env, tool_session, permissions)
        result.notes = list(result.notes or []) + dependency_notes
        return result

    def _run_node_like(self, run_id: str, language: str, source_path: Path, project_root: Path, stdin_text: str, env: dict[str, str], tool_session: dict[str, Any], permissions: dict[str, bool]) -> RunResult:
        executable = shutil.which("node")
        if not executable:
            raise RuntimeError("node ist auf dem Server nicht verfuegbar")
        return self._execute(run_id, language, [executable, str(source_path)], project_root, stdin_text, env, tool_session, permissions)

    def _run_cpp(self, run_id: str, source_path: Path, run_root: Path, project_root: Path, stdin_text: str, env: dict[str, str], tool_session: dict[str, Any], permissions: dict[str, bool]) -> RunResult:
        compiler = shutil.which("g++") or shutil.which("clang++")
        if not compiler:
            raise RuntimeError("g++ oder clang++ ist auf dem Server nicht verfuegbar")
        build_root = project_root / ".nova-build"
        build_root.mkdir(parents=True, exist_ok=True)
        binary = build_root / ("program.exe" if os.name == "nt" else "program")
        compile_command = [compiler, "-std=c++20", "-O2", str(source_path), "-o", str(binary)]
        compile_result = self._execute_raw(compile_command, project_root, "", env)
        if compile_result.returncode != 0:
            return RunResult(run_id, "cpp", compile_command, compile_result.stdout, compile_result.stderr, compile_result.returncode, compile_result.duration_ms, notes=self._network_notes(permissions), tool_session=tool_session)
        run_result = self._execute(run_id, "cpp", [str(binary)], project_root, stdin_text, env, tool_session, permissions)
        run_result.stdout = (compile_result.stdout + run_result.stdout).strip() + ("\n" if (compile_result.stdout or run_result.stdout) else "")
        return run_result

    def _run_java(self, run_id: str, source_path: Path, run_root: Path, project_root: Path, stdin_text: str, env: dict[str, str], tool_session: dict[str, Any], permissions: dict[str, bool]) -> RunResult:
        javac = shutil.which("javac")
        java = shutil.which("java")
        if not javac or not java:
            raise RuntimeError("javac und java muessen auf dem Server vorhanden sein")
        build_root = project_root / ".nova-build"
        build_root.mkdir(parents=True, exist_ok=True)
        compile_command = [javac, "-d", str(build_root), str(source_path)]
        compile_result = self._execute_raw(compile_command, project_root, "", env)
        if compile_result.returncode != 0:
            return RunResult(run_id, "java", compile_command, compile_result.stdout, compile_result.stderr, compile_result.returncode, compile_result.duration_ms, notes=self._network_notes(permissions), tool_session=tool_session)
        run_result = self._execute(run_id, "java", [java, "-cp", str(build_root), source_path.stem], project_root, stdin_text, env, tool_session, permissions)
        run_result.stdout = (compile_result.stdout + run_result.stdout).strip() + ("\n" if (compile_result.stdout or run_result.stdout) else "")
        return run_result

    def _run_rust(self, run_id: str, source_path: Path, run_root: Path, project_root: Path, stdin_text: str, env: dict[str, str], tool_session: dict[str, Any], permissions: dict[str, bool]) -> RunResult:
        cargo_manifest = project_root / "Cargo.toml"
        cargo = shutil.which("cargo")
        if cargo_manifest.exists() and cargo:
            return self._execute(run_id, "rust", [cargo, "run", "--manifest-path", str(cargo_manifest)], project_root, stdin_text, env, tool_session, permissions)
        rustc = shutil.which("rustc")
        if not rustc:
            raise RuntimeError("rustc ist auf dem Server nicht verfuegbar")
        build_root = project_root / ".nova-build"
        build_root.mkdir(parents=True, exist_ok=True)
        binary = build_root / ("program.exe" if os.name == "nt" else "program")
        compile_command = [rustc, str(source_path), "-o", str(binary)]
        compile_result = self._execute_raw(compile_command, project_root, "", env)
        if compile_result.returncode != 0:
            return RunResult(run_id, "rust", compile_command, compile_result.stdout, compile_result.stderr, compile_result.returncode, compile_result.duration_ms, notes=self._network_notes(permissions), tool_session=tool_session)
        run_result = self._execute(run_id, "rust", [str(binary)], project_root, stdin_text, env, tool_session, permissions)
        run_result.stdout = (compile_result.stdout + run_result.stdout).strip() + ("\n" if (compile_result.stdout or run_result.stdout) else "")
        return run_result

    def _run_npm(self, run_id: str, project_root: Path, payload: dict[str, Any], stdin_text: str, env: dict[str, str], tool_session: dict[str, Any], permissions: dict[str, bool]) -> RunResult:
        command_text = str(payload.get("command") or "").strip()
        if not command_text:
            raise ValueError("npm benoetigt ein Kommando, z. B. `run dev` oder `install`.")
        tokens = shlex.split(command_text, posix=False)
        if not tokens:
            raise ValueError("npm Kommando ist leer.")
        first = tokens[0].lower()
        if first not in {"install", "run", "test", "ci", "list"}:
            raise PermissionError("Nur `install`, `run`, `test`, `ci` und `list` sind fuer npm erlaubt.")
        if first in {"install", "ci"} and not permissions.get("web.access", False):
            raise PermissionError("npm Installationspfade sind ohne Webfreigabe gesperrt.")
        npm = shutil.which("npm.cmd") or shutil.which("npm")
        if not npm:
            raise RuntimeError("npm ist auf dem Server nicht verfuegbar")
        return self._execute(run_id, "npm", [npm, *tokens], project_root, stdin_text, env, tool_session, permissions)

    def _ensure_python_dependencies_process(self, workspace_root: Path, env: dict[str, str], permissions: dict[str, bool]) -> tuple[Path | None, list[str], str]:
        requirements_path = self._python_requirements_file(workspace_root)
        if requirements_path is None:
            return None, [], ""
        deps_root = workspace_root / ".nova-python" / "site-packages"
        cache_root = self._python_dependency_cache_dir(requirements_path, "process")
        if self._restore_dependency_cache(deps_root, cache_root):
            return deps_root, ["Python-Abhaengigkeiten wurden aus dem lokalen Server-Cache bereitgestellt."], ""
        if not permissions.get("web.access", False):
            return None, [], (
                "Dieses Python-Projekt benoetigt Pakete aus requirements.txt, aber Webzugriff ist fuer diese Sitzung nicht freigegeben "
                "und auf dem Server liegt noch kein Paket-Cache fuer dieses Projekt vor.\n\n"
                "Loesung:\n"
                "1. Lehrkraft/Admin gibt den Webzugriff fuer die Erstinstallation frei oder\n"
                "2. die Abhaengigkeiten werden einmalig serverseitig vorgewarmt."
            )
        deps_root.parent.mkdir(parents=True, exist_ok=True)
        executable = shutil.which("python") or shutil.which("py")
        if not executable:
            return None, [], "python ist auf dem Server nicht verfuegbar"
        install_command = [executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-compile", "--target", str(deps_root), "-r", str(requirements_path)]
        if Path(executable).name.lower() in {"py", "py.exe"}:
            install_command = [executable, "-3", "-m", "pip", "install", "--disable-pip-version-check", "--no-compile", "--target", str(deps_root), "-r", str(requirements_path)]
        install_result = self._execute_raw(install_command, workspace_root, "", env, timeout_seconds=max(self.config.run_timeout_seconds, 300))
        if install_result.returncode != 0:
            return None, [], (
                "Python-Abhaengigkeiten aus requirements.txt konnten nicht installiert werden.\n\n"
                f"{install_result.stderr or install_result.stdout}".strip()
            )
        self._store_dependency_cache(deps_root, cache_root)
        return deps_root, ["Python-Abhaengigkeiten wurden serverseitig aus requirements.txt installiert und fuer spaetere Laeufe gecacht."], ""

    def _ensure_python_dependencies_container(
        self,
        runtime_executable: str,
        image: str,
        container_workspace: Path,
        env: dict[str, str],
        permissions: dict[str, bool],
    ) -> tuple[Path | None, list[str], str]:
        requirements_path = self._python_requirements_file(container_workspace)
        if requirements_path is None:
            return None, [], ""
        deps_root = container_workspace / ".nova-python" / "site-packages"
        cache_root = self._python_dependency_cache_dir(requirements_path, f"container:{image}")
        if self._restore_dependency_cache(deps_root, cache_root):
            return deps_root, ["Python-Abhaengigkeiten wurden aus dem lokalen Server-Cache bereitgestellt."], ""
        if not permissions.get("web.access", False):
            return None, [], (
                "Dieses Python-Projekt benoetigt Pakete aus requirements.txt, aber Webzugriff ist fuer diese Sitzung nicht freigegeben "
                "und auf dem Server liegt noch kein Paket-Cache fuer dieses Projekt vor.\n\n"
                "Loesung:\n"
                "1. Lehrkraft/Admin gibt den Webzugriff fuer die Erstinstallation frei oder\n"
                "2. die Abhaengigkeiten werden einmalig serverseitig vorgewarmt."
            )
        deps_root.parent.mkdir(parents=True, exist_ok=True)
        install_env = self._containerized_env(env)
        install_command = self._container_wrapped_command(
            self._container_base_command(runtime_executable, image, container_workspace, container_workspace, permissions, container_env=install_env),
            ["python", "-m", "pip", "install", "--disable-pip-version-check", "--no-compile", "--target", "/workspace/.nova-python/site-packages", "-r", "/workspace/requirements.txt"],
        )
        install_result = self._execute_raw(install_command, container_workspace, "", env, timeout_seconds=max(self.config.run_timeout_seconds, 300))
        if install_result.returncode != 0:
            return None, [], (
                "Python-Abhaengigkeiten aus requirements.txt konnten im Container nicht installiert werden.\n\n"
                f"{install_result.stderr or install_result.stdout}".strip()
            )
        self._store_dependency_cache(deps_root, cache_root)
        return deps_root, ["Python-Abhaengigkeiten wurden serverseitig aus requirements.txt installiert und fuer spaetere Laeufe gecacht."], ""

    def _ensure_python_gui_container_image(self, runtime_executable: str, base_image: str, permissions: dict[str, bool]) -> tuple[str, list[str], str]:
        image_tag = f"nova-school-python-gui:{hashlib.sha256(base_image.encode('utf-8')).hexdigest()[:12]}"
        inspect_command = [runtime_executable, "image", "inspect", image_tag]
        inspect_result = self._execute_raw(inspect_command, self.config.base_path, "", dict(os.environ), timeout_seconds=max(self.config.run_timeout_seconds, 60))
        if inspect_result.returncode == 0:
            return image_tag, ["Python-GUI-Lauf nutzt ein serverseitig vorbereitetes GUI-Container-Image mit virtueller Anzeige."], ""
        if not permissions.get("web.access", False):
            return base_image, [], (
                "Fuer Python-GUI-Projekte wird ein GUI-faehiges Container-Image mit tkinter/Xvfb benoetigt.\n\n"
                "Dieses Image ist auf dem Server noch nicht vorbereitet, und die aktuelle Sitzung hat keinen Webzugriff fuer die Erstbereitstellung.\n\n"
                "Loesung:\n"
                "1. Lehrkraft/Admin startet den Lauf einmal mit temporaerer Webfreigabe oder\n"
                "2. das GUI-Image wird vor dem Unterricht serverseitig vorgewarmt."
            )

        build_root = self.config.data_path / "container_build" / image_tag.replace(":", "_")
        build_root.mkdir(parents=True, exist_ok=True)
        dockerfile_path = build_root / "Dockerfile"
        dockerfile_path.write_text(
            textwrap.dedent(
                f"""\
                FROM {base_image}

                RUN apt-get update \\
                    && apt-get install -y --no-install-recommends python3-tk tk xvfb imagemagick \\
                    && rm -rf /var/lib/apt/lists/*
                """
            ),
            encoding="utf-8",
        )
        build_command = [runtime_executable, "build", "-t", image_tag, str(build_root)]
        build_result = self._execute_raw(build_command, build_root, "", dict(os.environ), timeout_seconds=max(self.config.run_timeout_seconds, 900))
        if build_result.returncode != 0:
            return base_image, [], (
                "Das Python-GUI-Container-Image konnte nicht vorbereitet werden.\n\n"
                f"{build_result.stderr or build_result.stdout}".strip()
            )
        return image_tag, ["Python-GUI-Lauf nutzt ein serverseitig vorbereitetes GUI-Container-Image mit virtueller Anzeige."], ""

    def _prepare_python_gui_scripts(self, container_workspace: Path, container_source_path: Path) -> tuple[Path, Path]:
        build_root = container_workspace / ".nova-build"
        build_root.mkdir(parents=True, exist_ok=True)
        relative_source = self._container_path(container_workspace, container_source_path)

        live_script = build_root / "python_gui_live.sh"
        live_script.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                set -eu
                exec xvfb-run -a python -u -I {shlex.quote(relative_source)}
                """
            ),
            encoding="utf-8",
        )
        os.chmod(live_script, 0o755)

        snapshot_script = build_root / "python_gui_snapshot.sh"
        snapshot_script.write_text(
            textwrap.dedent(
                f"""\
                #!/bin/sh
                set -eu
                mkdir -p /workspace/.nova-build
                rm -f /workspace/.nova-build/gui-preview.png
                python -u -I {shlex.quote(relative_source)} &
                pid=$!
                sleep 2
                if command -v import >/dev/null 2>&1; then
                  import -window root /workspace/.nova-build/gui-preview.png >/dev/null 2>&1 || true
                fi
                kill "$pid" >/dev/null 2>&1 || true
                wait "$pid" >/dev/null 2>&1 || true
                exit 0
                """
            ),
            encoding="utf-8",
        )
        os.chmod(snapshot_script, 0o755)
        return snapshot_script, live_script

    def _prepare_live_process(
        self,
        session_id: str,
        run_id: str,
        language: str,
        source_path: Path,
        run_root: Path,
        project_root: Path,
        env: dict[str, str],
        tool_session: dict[str, Any],
        permissions: dict[str, bool],
        payload: dict[str, Any],
    ) -> LivePreparedRun:
        if language == "python":
            deps_root, dependency_notes, dependency_error = self._ensure_python_dependencies_process(project_root, env, permissions)
            if dependency_error:
                return LivePreparedRun(session_id, run_id, language, ["pip", "install"], project_root, env, self._backend_notes(permissions, "process"), tool_session, prelude_stderr=dependency_error, failed_returncode=2)
            executable = shutil.which("python") or shutil.which("py")
            if not executable:
                raise RuntimeError("python ist auf dem Server nicht verfuegbar")
            bootstrap_path = self._write_python_bootstrap(project_root)
            prepared_env = self._python_entry_env(env, str(source_path), str(deps_root) if deps_root else None)
            command = [executable, "-u", "-I", str(bootstrap_path)]
            if Path(executable).name.lower() in {"py", "py.exe"}:
                command = [executable, "-3", "-u", "-I", str(bootstrap_path)]
            return LivePreparedRun(session_id, run_id, language, command, project_root, prepared_env, self._backend_notes(permissions, "process") + dependency_notes, tool_session)

        if language in {"javascript", "node"}:
            executable = shutil.which("node")
            if not executable:
                raise RuntimeError("node ist auf dem Server nicht verfuegbar")
            return LivePreparedRun(session_id, run_id, language, [executable, str(source_path)], project_root, env, self._backend_notes(permissions, "process"), tool_session)

        if language == "cpp":
            compiler = shutil.which("g++") or shutil.which("clang++")
            if not compiler:
                raise RuntimeError("g++ oder clang++ ist auf dem Server nicht verfuegbar")
            build_root = project_root / ".nova-build"
            build_root.mkdir(parents=True, exist_ok=True)
            binary = build_root / ("program.exe" if os.name == "nt" else "program")
            compile_command = [compiler, "-std=c++20", "-O2", str(source_path), "-o", str(binary)]
            compile_result = self._execute_raw(compile_command, project_root, "", env)
            if compile_result.returncode != 0:
                return LivePreparedRun(session_id, run_id, language, compile_command, project_root, env, self._backend_notes(permissions, "process"), tool_session, prelude_stdout=compile_result.stdout, prelude_stderr=compile_result.stderr, failed_returncode=compile_result.returncode)
            return LivePreparedRun(session_id, run_id, language, [str(binary)], project_root, env, self._backend_notes(permissions, "process"), tool_session, prelude_stdout=compile_result.stdout)

        if language == "java":
            javac = shutil.which("javac")
            java = shutil.which("java")
            if not javac or not java:
                raise RuntimeError("javac und java muessen auf dem Server vorhanden sein")
            build_root = project_root / ".nova-build"
            build_root.mkdir(parents=True, exist_ok=True)
            compile_command = [javac, "-d", str(build_root), str(source_path)]
            compile_result = self._execute_raw(compile_command, project_root, "", env)
            if compile_result.returncode != 0:
                return LivePreparedRun(session_id, run_id, language, compile_command, project_root, env, self._backend_notes(permissions, "process"), tool_session, prelude_stdout=compile_result.stdout, prelude_stderr=compile_result.stderr, failed_returncode=compile_result.returncode)
            return LivePreparedRun(session_id, run_id, language, [java, "-cp", str(build_root), source_path.stem], project_root, env, self._backend_notes(permissions, "process"), tool_session, prelude_stdout=compile_result.stdout)

        if language == "rust":
            cargo_manifest = project_root / "Cargo.toml"
            cargo = shutil.which("cargo")
            if cargo_manifest.exists() and cargo:
                return LivePreparedRun(session_id, run_id, language, [cargo, "run", "--manifest-path", str(cargo_manifest)], project_root, env, self._backend_notes(permissions, "process"), tool_session)
            rustc = shutil.which("rustc")
            if not rustc:
                raise RuntimeError("rustc ist auf dem Server nicht verfuegbar")
            build_root = project_root / ".nova-build"
            build_root.mkdir(parents=True, exist_ok=True)
            binary = build_root / ("program.exe" if os.name == "nt" else "program")
            compile_command = [rustc, str(source_path), "-o", str(binary)]
            compile_result = self._execute_raw(compile_command, project_root, "", env)
            if compile_result.returncode != 0:
                return LivePreparedRun(session_id, run_id, language, compile_command, project_root, env, self._backend_notes(permissions, "process"), tool_session, prelude_stdout=compile_result.stdout, prelude_stderr=compile_result.stderr, failed_returncode=compile_result.returncode)
            return LivePreparedRun(session_id, run_id, language, [str(binary)], project_root, env, self._backend_notes(permissions, "process"), tool_session, prelude_stdout=compile_result.stdout)

        if language == "npm":
            command_text = str(payload.get("command") or "").strip()
            if not command_text:
                raise ValueError("npm benoetigt ein Kommando, z. B. `run dev` oder `install`.")
            tokens = shlex.split(command_text, posix=False)
            if not tokens:
                raise ValueError("npm Kommando ist leer.")
            first = tokens[0].lower()
            if first not in {"install", "run", "test", "ci", "list"}:
                raise PermissionError("Nur `install`, `run`, `test`, `ci` und `list` sind fuer npm erlaubt.")
            if first in {"install", "ci"} and not permissions.get("web.access", False):
                raise PermissionError("npm Installationspfade sind ohne Webfreigabe gesperrt.")
            npm = shutil.which("npm.cmd") or shutil.which("npm")
            if not npm:
                raise RuntimeError("npm ist auf dem Server nicht verfuegbar")
            return LivePreparedRun(session_id, run_id, language, [npm, *tokens], project_root, env, self._backend_notes(permissions, "process"), tool_session)

        raise ValueError(f"unsupported language for live mode: {language}")

    def _prepare_live_containerized(
        self,
        session_id: str,
        run_id: str,
        language: str,
        source_path: Path,
        run_root: Path,
        project_root: Path,
        env: dict[str, str],
        tool_session: dict[str, Any],
        permissions: dict[str, bool],
        payload: dict[str, Any],
    ) -> LivePreparedRun:
        runtime = self._container_runtime(payload)
        runtime_executable = shutil.which(runtime) or runtime
        image = self._container_image(language, payload)
        healthy, runtime_error = self._container_runtime_health(runtime_executable, image)
        if not healthy:
            notes = self._backend_notes(permissions, "container", Path(runtime_executable).name, image)
            return LivePreparedRun(session_id, run_id, language, [runtime_executable, "info"], project_root, env, notes, tool_session, prelude_stderr=runtime_error, failed_returncode=2)
        container_workspace = self._prepare_container_workspace(project_root, run_root)
        container_source_path = container_workspace / source_path.relative_to(project_root)
        notes = self._backend_notes(permissions, "container", Path(runtime_executable).name, image)
        wants_pty = bool((payload.get("terminal") if isinstance(payload.get("terminal"), dict) else {}).get("pty"))
        container_env = self._containerized_env(env)
        base_command = self._container_base_command(runtime_executable, image, project_root, container_workspace, permissions, container_env=container_env)
        pty_base_command = self._container_base_command(runtime_executable, image, project_root, container_workspace, permissions, tty=True, container_env=container_env) if wants_pty else None
        inspect_command = [runtime_executable, "image", "inspect", image]
        inspect_result = self._execute_raw(inspect_command, project_root, "", dict(os.environ))
        if inspect_result.returncode != 0:
            stderr = self._container_runtime_error_message(runtime_executable, image, inspect_result.stderr)
            return LivePreparedRun(session_id, run_id, language, inspect_command, project_root, env, notes, tool_session, prelude_stdout=inspect_result.stdout, prelude_stderr=stderr, failed_returncode=inspect_result.returncode)

        if language == "python":
            gui_frameworks = self._detect_python_gui_frameworks(language, source_path, payload)
            deps_root, dependency_notes, dependency_error = self._ensure_python_dependencies_container(runtime_executable, image, container_workspace, env, permissions)
            if dependency_error:
                return LivePreparedRun(session_id, run_id, language, ["pip", "install"], project_root, env, notes, tool_session, prelude_stderr=dependency_error, failed_returncode=2)
            notes = notes + dependency_notes
            if gui_frameworks:
                image, gui_notes, gui_error = self._ensure_python_gui_container_image(runtime_executable, image, permissions)
                if gui_error:
                    return LivePreparedRun(session_id, run_id, language, ["docker", "build"], project_root, env, notes, tool_session, prelude_stderr=gui_error, failed_returncode=2)
                notes = self._backend_notes(permissions, "container", Path(runtime_executable).name, image) + dependency_notes + gui_notes + [
                    "Python-GUI erkannt. Live-Lauf startet in einer virtuellen Anzeige; fuer sichtbare Browser-Vorschau ist aktuell der normale Datei-Lauf im GUI-Snapshot-Modus vorgesehen."
                ]
            container_env = self._python_entry_env(
                self._containerized_env(env),
                self._container_path(container_workspace, container_source_path),
                self._container_path(container_workspace, deps_root) if deps_root else None,
            )
            base_command = self._container_base_command(runtime_executable, image, container_workspace, container_workspace, permissions, container_env=container_env)
            pty_base_command = self._container_base_command(runtime_executable, image, container_workspace, container_workspace, permissions, tty=True, container_env=container_env) if wants_pty else None
            bootstrap_path = self._write_python_bootstrap(container_workspace)
            if gui_frameworks:
                _snapshot_script, live_script = self._prepare_python_gui_scripts(container_workspace, container_source_path)
                inner_command = ["/bin/sh", self._container_path(container_workspace, live_script)]
            else:
                inner_command = ["python", "-u", "-I", self._container_path(container_workspace, bootstrap_path)]
            return LivePreparedRun(session_id, run_id, language, self._container_wrapped_command(base_command, inner_command), project_root, env, notes, tool_session, pty_command=(self._container_wrapped_command(pty_base_command, inner_command) if pty_base_command else None))
        if language in {"javascript", "node"}:
            inner_command = ["node", self._container_path(project_root, source_path)]
            return LivePreparedRun(session_id, run_id, language, self._container_wrapped_command(base_command, inner_command), project_root, env, notes, tool_session, pty_command=(self._container_wrapped_command(pty_base_command, inner_command) if pty_base_command else None))
        if language == "cpp":
            container_source = self._container_path(project_root, source_path)
            build_root = project_root / ".nova-build"
            build_root.mkdir(parents=True, exist_ok=True)
            container_binary = self._container_path(project_root, build_root / ("program.exe" if os.name == "nt" else "program"))
            compile = self._execute_container_raw(runtime_executable, image, ["g++", "-std=c++20", "-O2", container_source, "-o", container_binary], project_root, container_workspace, "", env, permissions)
            if compile.returncode != 0:
                return LivePreparedRun(session_id, run_id, language, compile.command or inspect_command, project_root, env, notes, tool_session, prelude_stdout=compile.stdout, prelude_stderr=compile.stderr, failed_returncode=compile.returncode)
            return LivePreparedRun(session_id, run_id, language, self._container_wrapped_command(base_command, [container_binary]), project_root, env, notes, tool_session, pty_command=(self._container_wrapped_command(pty_base_command, [container_binary]) if pty_base_command else None), prelude_stdout=compile.stdout)
        if language == "java":
            container_source = self._container_path(project_root, source_path)
            build_root = project_root / ".nova-build"
            build_root.mkdir(parents=True, exist_ok=True)
            container_output = self._container_path(project_root, build_root)
            compile = self._execute_container_raw(runtime_executable, image, ["javac", "-d", container_output, container_source], project_root, container_workspace, "", env, permissions)
            if compile.returncode != 0:
                return LivePreparedRun(session_id, run_id, language, compile.command or inspect_command, project_root, env, notes, tool_session, prelude_stdout=compile.stdout, prelude_stderr=compile.stderr, failed_returncode=compile.returncode)
            inner_command = ["java", "-cp", container_output, source_path.stem]
            return LivePreparedRun(session_id, run_id, language, self._container_wrapped_command(base_command, inner_command), project_root, env, notes, tool_session, pty_command=(self._container_wrapped_command(pty_base_command, inner_command) if pty_base_command else None), prelude_stdout=compile.stdout)
        if language == "rust":
            cargo_manifest = project_root / "Cargo.toml"
            if cargo_manifest.exists():
                manifest_path = self._container_path(project_root, cargo_manifest)
                inner_command = ["cargo", "run", "--manifest-path", manifest_path]
                return LivePreparedRun(session_id, run_id, language, self._container_wrapped_command(base_command, inner_command), project_root, env, notes, tool_session, pty_command=(self._container_wrapped_command(pty_base_command, inner_command) if pty_base_command else None))
            container_source = self._container_path(project_root, source_path)
            build_root = project_root / ".nova-build"
            build_root.mkdir(parents=True, exist_ok=True)
            container_binary = self._container_path(project_root, build_root / ("program.exe" if os.name == "nt" else "program"))
            compile = self._execute_container_raw(runtime_executable, image, ["rustc", container_source, "-o", container_binary], project_root, container_workspace, "", env, permissions)
            if compile.returncode != 0:
                return LivePreparedRun(session_id, run_id, language, compile.command or inspect_command, project_root, env, notes, tool_session, prelude_stdout=compile.stdout, prelude_stderr=compile.stderr, failed_returncode=compile.returncode)
            return LivePreparedRun(session_id, run_id, language, self._container_wrapped_command(base_command, [container_binary]), project_root, env, notes, tool_session, pty_command=(self._container_wrapped_command(pty_base_command, [container_binary]) if pty_base_command else None), prelude_stdout=compile.stdout)
        if language == "npm":
            command_text = str(payload.get("command") or "").strip()
            if not command_text:
                raise ValueError("npm benoetigt ein Kommando, z. B. `run dev` oder `install`.")
            tokens = shlex.split(command_text, posix=False)
            if not tokens:
                raise ValueError("npm Kommando ist leer.")
            first = tokens[0].lower()
            if first not in {"install", "run", "test", "ci", "list"}:
                raise PermissionError("Nur `install`, `run`, `test`, `ci` und `list` sind fuer npm erlaubt.")
            if first in {"install", "ci"} and not permissions.get("web.access", False):
                raise PermissionError("npm Installationspfade sind ohne Webfreigabe gesperrt.")
            inner_command = ["npm", *tokens]
            return LivePreparedRun(session_id, run_id, language, self._container_wrapped_command(base_command, inner_command), project_root, env, notes, tool_session, pty_command=(self._container_wrapped_command(pty_base_command, inner_command) if pty_base_command else None))

        raise ValueError(f"unsupported language for live container mode: {language}")

    def _execute(self, run_id: str, language: str, command: list[str], cwd: Path, stdin_text: str, env: dict[str, str], tool_session: dict[str, Any], permissions: dict[str, bool]) -> RunResult:
        result = self._execute_raw(command, cwd, stdin_text, env)
        return RunResult(
            run_id=run_id,
            language=language,
            command=command,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            duration_ms=result.duration_ms,
            notes=self._backend_notes(permissions, "process"),
            tool_session=tool_session,
        )

    def _execute_container(self, run_id: str, language: str, runtime_executable: str, image: str, inner_command: list[str], project_root: Path, container_workspace: Path, stdin_text: str, env: dict[str, str], tool_session: dict[str, Any], permissions: dict[str, bool]) -> RunResult:
        result = self._execute_container_raw(runtime_executable, image, inner_command, project_root, container_workspace, stdin_text, env, permissions)
        return RunResult(
            run_id=run_id,
            language=language,
            command=result.command,
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            duration_ms=result.duration_ms,
            notes=self._backend_notes(permissions, "container", Path(runtime_executable).name, image),
            tool_session=tool_session,
        )

    def _execute_container_raw(self, runtime_executable: str, image: str, inner_command: list[str], project_root: Path, container_workspace: Path, stdin_text: str, env: dict[str, str], permissions: dict[str, bool]) -> "_RawResult":
        command = self._container_wrapped_command(
            self._container_base_command(runtime_executable, image, project_root, container_workspace, permissions, container_env=self._containerized_env(env)),
            inner_command,
        )
        result = self._execute_raw(command, project_root, stdin_text, env)
        result.command = command
        return result

    def _prepare_container_workspace(self, source_root: Path, run_root: Path) -> Path:
        container_workspace = run_root / "container-workspace"
        ignored_names = {".nova-build", ".nova-cache", ".nova-tmp"}
        self._mirror_tree_securely(source_root, container_workspace, ignored_names)
        (container_workspace / ".nova-build").mkdir(parents=True, exist_ok=True)
        (container_workspace / ".nova-cache").mkdir(parents=True, exist_ok=True)
        (container_workspace / ".nova-tmp").mkdir(parents=True, exist_ok=True)
        return container_workspace

    def _mirror_tree_securely(self, source_root: Path, target_root: Path, ignored_names: set[str]) -> None:
        if target_root.exists():
            shutil.rmtree(target_root, ignore_errors=True)
        target_root.mkdir(parents=True, exist_ok=True)
        self._copy_tree_entries_securely(source_root, target_root, ignored_names)

    def _copy_tree_entries_securely(self, source_dir: Path, target_dir: Path, ignored_names: set[str]) -> None:
        with os.scandir(source_dir) as entries:
            for entry in entries:
                if entry.name in ignored_names:
                    continue
                source_path = Path(entry.path)
                target_path = target_dir / entry.name
                if self._is_link_like(source_path):
                    raise PermissionError(f"Symbolische Links oder Junctions sind in Lauf-Workspaces nicht erlaubt: {source_path}")
                if entry.is_dir(follow_symlinks=False):
                    target_path.mkdir(parents=True, exist_ok=True)
                    self._copy_tree_entries_securely(source_path, target_path, ignored_names)
                    continue
                if entry.is_file(follow_symlinks=False):
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)
                    continue
                raise PermissionError(f"Nicht unterstuetzter Dateityp im Projekt-Workspace: {source_path}")

    @staticmethod
    def _is_link_like(path: Path) -> bool:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if callable(is_junction):
            try:
                return bool(is_junction())
            except OSError:
                return True
        return False

    def _execution_env(self, project_root: Path, web_access: bool) -> dict[str, str]:
        env = dict(os.environ)
        tmp_root = project_root / ".nova-tmp"
        cache_root = project_root / ".nova-cache"
        tmp_root.mkdir(parents=True, exist_ok=True)
        cache_root.mkdir(parents=True, exist_ok=True)
        env["NOVA_SCHOOL_NETWORK"] = "on" if web_access else "off"
        env["PYTHONNOUSERSITE"] = "1"
        env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
        env["TERM"] = env.get("TERM") or "xterm-256color"
        env["COLORTERM"] = "truecolor"
        env["CLICOLOR_FORCE"] = "1"
        env["FORCE_COLOR"] = "1"
        env["HOME"] = str(project_root)
        env["USERPROFILE"] = str(project_root)
        env["TMP"] = str(tmp_root)
        env["TEMP"] = str(tmp_root)
        env["TMPDIR"] = str(tmp_root)
        env["XDG_CACHE_HOME"] = str(cache_root)
        if not web_access:
            env["NOVA_SCHOOL_WEB_POLICY"] = "off"
            for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy", "npm_config_proxy", "npm_config_https_proxy"]:
                env[key] = ""
            env["NO_PROXY"] = "*"
        else:
            proxy_url = str(self._setting("web_proxy_url", "") or "").strip()
            if self._setting_bool("web_proxy_required", False) and not proxy_url:
                raise PermissionError("Webzugriff ist nur mit konfiguriertem Proxy erlaubt.")
            if proxy_url:
                env["NOVA_SCHOOL_WEB_POLICY"] = "proxy"
                for key in ["HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy", "npm_config_proxy", "npm_config_https_proxy"]:
                    env[key] = proxy_url
                no_proxy = str(self._setting("web_proxy_no_proxy", "") or "").strip()
                if no_proxy:
                    env["NO_PROXY"] = no_proxy
            else:
                env["NOVA_SCHOOL_WEB_POLICY"] = "open"
        return env

    @staticmethod
    def _containerized_env(env: dict[str, str]) -> dict[str, str]:
        blocked = {
            "path",
            "pathext",
            "comspec",
            "prompt",
            "systemroot",
            "windir",
            "psmodulepath",
            "appdata",
            "localappdata",
            "programdata",
            "programfiles",
            "programfiles(x86)",
            "programw6432",
            "commonprogramfiles",
            "commonprogramfiles(x86)",
            "commonprogramw6432",
            "allusersprofile",
            "onedrive",
            "public",
            "homedrive",
            "homepath",
        }
        payload = {key: value for key, value in dict(env).items() if key.strip().lower() not in blocked}
        payload["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        payload["HOME"] = "/workspace"
        payload["USERPROFILE"] = "/workspace"
        payload["TMP"] = "/tmp"
        payload["TEMP"] = "/tmp"
        payload["TMPDIR"] = "/tmp"
        payload["XDG_CACHE_HOME"] = "/workspace/.nova-cache"
        return payload

    def _network_notes(self, permissions: dict[str, bool]) -> list[str]:
        if permissions.get("web.access", False):
            proxy_url = str(self._setting("web_proxy_url", "") or "").strip()
            if proxy_url:
                if self._setting_bool("web_proxy_required", False):
                    return [f"Webzugriff ist freigegeben und serverseitig auf Proxy-Pfad erzwungen: {proxy_url}"]
                return [f"Webzugriff ist freigegeben und ueber Proxy-Pfad konfiguriert: {proxy_url}"]
            return ["Webzugriff ist fuer diese Sitzung freigegeben."]
        return ["Webzugriff ist serverseitig deaktiviert; netzwerknahe Projektpfade werden nach Moeglichkeit blockiert."]

    def _backend_notes(self, permissions: dict[str, bool], backend: str, runtime: str = "", image: str = "") -> list[str]:
        notes = []
        if backend == "container":
            runtime_label = runtime or self._container_runtime({})
            if image:
                notes.append(f"Container-Isolation aktiv ({runtime_label}, Image: {image}).")
            else:
                notes.append(f"Container-Isolation aktiv ({runtime_label}).")
            notes.append("Bei deaktiviertem Webzugriff wird der Container isoliert ohne externes Projekt-Webnetz gestartet.")
            notes.append("Container-Haertung aktiv: read-only Root-FS und materialisierter Schreib-Workspace pro Run ohne Live-Quell-Mount.")
            if os.name == "nt" and runtime_label.startswith("docker"):
                notes.append("Container-Haertung aktiv: `--pids-limit`, `--cap-drop ALL`, `no-new-privileges`, Docker-Builtin-Seccomp, `ulimit`.")
            else:
                notes.append("Container-Haertung aktiv: `--pids-limit`, `--cap-drop ALL`, `no-new-privileges`, `seccomp`, `ulimit`.")
        else:
            notes.append("Unsicherer Host-Prozess-Runner aktiv. Dieser Modus ist nur als ausdruecklicher Admin-/Lehrkraft-Fallback gedacht.")
        notes.extend(self._network_notes(permissions))
        return notes

    def _runner_backend(self, payload: dict[str, Any]) -> str:
        explicit = str(payload.get("runner_backend") or "").strip().lower()
        if explicit in {"process", "container"}:
            return explicit
        configured = str(self._setting("runner_backend", "container")).strip().lower() or "container"
        return configured if configured in {"process", "container"} else "container"

    def resolve_backend(self, session: Any, payload: dict[str, Any] | None = None, *, purpose: str = "Ausfuehrung") -> str:
        requested = self._runner_backend(payload or {})
        if requested == "container":
            return "container"
        if not self._unsafe_process_backend_enabled():
            raise PermissionError(f"{purpose}: Host-Prozess-Runner ist aus Sicherheitsgruenden deaktiviert. Nutze Container-Backend.")
        if not bool(getattr(session, "is_teacher", False)):
            raise PermissionError(f"{purpose}: Host-Prozess-Runner ist nur fuer Lehrkraefte oder Administration freigegeben.")
        return "process"

    @staticmethod
    def _session_role(session: Any) -> str:
        return str(getattr(session, "role", "student") or "student")

    def _container_runtime(self, payload: dict[str, Any]) -> str:
        explicit = str(payload.get("container_runtime") or "").strip().lower()
        if explicit in {"docker", "podman"}:
            return explicit
        configured = str(self._setting("container_runtime", "docker")).strip().lower() or "docker"
        return configured if configured in {"docker", "podman"} else "docker"

    def _container_image(self, language: str, payload: dict[str, Any]) -> str:
        explicit = str(payload.get("container_image") or "").strip()
        if explicit:
            return explicit
        image_key = {
            "python": "container_image_python",
            "javascript": "container_image_node",
            "node": "container_image_node",
            "npm": "container_image_node",
            "cpp": "container_image_cpp",
            "java": "container_image_java",
            "rust": "container_image_rust",
        }.get(language, "container_image_python")
        default_key = {
            "container_image_python": DEFAULT_CONTAINER_IMAGES["python"],
            "container_image_node": DEFAULT_CONTAINER_IMAGES["node"],
            "container_image_cpp": DEFAULT_CONTAINER_IMAGES["cpp"],
            "container_image_java": DEFAULT_CONTAINER_IMAGES["java"],
            "container_image_rust": DEFAULT_CONTAINER_IMAGES["rust"],
        }[image_key]
        return str(self._setting(image_key, default_key)).strip() or default_key

    def _container_base_command(
        self,
        runtime_executable: str,
        image: str,
        source_root: Path,
        workspace_root: Path,
        permissions: dict[str, bool],
        tty: bool = False,
        *,
        network_mode_override: str | None = None,
        published_ports: list[str] | None = None,
        container_name: str = "",
        network_aliases: list[str] | None = None,
        workdir: str = "/workspace",
        container_env: dict[str, str] | None = None,
    ) -> list[str]:
        network_mode = network_mode_override or ("bridge" if permissions.get("web.access", False) else "none")
        memory = str(self._setting("container_memory_limit", "512m"))
        cpus = str(self._setting("container_cpu_limit", "1.5"))
        pids_limit = str(self._setting("container_pids_limit", "128"))
        file_size_limit = str(self._setting("container_file_size_limit_kb", "65536"))
        nofile_limit = str(self._setting("container_nofile_limit", "256"))
        tmpfs_size = str(self._setting("container_tmpfs_limit", "64m"))
        workspace_mount = f"{workspace_root.resolve(strict=False)}:/workspace"
        oci_runtime = str(self._setting("container_oci_runtime", "") or "").strip()
        command = [
            runtime_executable,
            "run",
            "--rm",
            "-i",
        ]
        if tty:
            command.append("-t")
        if container_name:
            command.extend(["--name", container_name])
        if oci_runtime:
            command.extend(["--runtime", oci_runtime])
        if network_mode:
            command.extend(["--network", network_mode])
        for alias in list(network_aliases or []):
            command.extend(["--network-alias", alias])
        for port in list(published_ports or []):
            command.extend(["-p", port])
        for key, value in dict(container_env or {}).items():
            command.extend(["-e", f"{key}={value}"])
        command.extend(
            [
                "--memory",
                memory,
                "--cpus",
                cpus,
                "--pids-limit",
                pids_limit,
                "--ulimit",
                f"fsize={file_size_limit}:{file_size_limit}",
                "--ulimit",
                f"nofile={nofile_limit}:{nofile_limit}",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--read-only",
                "--tmpfs",
                f"/tmp:rw,noexec,nosuid,nodev,size={tmpfs_size}",
                "--tmpfs",
                f"/var/tmp:rw,noexec,nosuid,nodev,size={tmpfs_size}",
                "-v",
                workspace_mount,
                "-w",
                workdir,
            ]
        )
        seccomp_opt = self._container_seccomp_option(Path(runtime_executable).name.lower())
        if seccomp_opt:
            command.extend(["--security-opt", seccomp_opt])
        command.append(image)
        return command

    @staticmethod
    def _container_wrapped_command(base_command: list[str], inner_command: list[str]) -> list[str]:
        return [*base_command, *inner_command]

    def _container_path(self, project_root: Path, target: Path) -> str:
        relative = target.resolve(strict=False).relative_to(project_root.resolve(strict=False)).as_posix()
        return f"/workspace/{relative}"

    def _setting(self, key: str, default: Any) -> Any:
        if self.repository is None:
            return default
        return self.repository.get_setting(key, default)

    def _setting_bool(self, key: str, default: bool) -> bool:
        value = self._setting(key, default)
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    def _unsafe_process_backend_enabled(self) -> bool:
        return self._setting_bool("unsafe_process_backend_enabled", False)

    def _container_seccomp_option(self, runtime_name: str) -> str | None:
        if not self._setting_bool("container_seccomp_enabled", True):
            return None
        profile_value = str(self._setting("container_seccomp_profile", "") or "").strip()
        profile_path = Path(profile_value).resolve(strict=False) if profile_value else (self.config.base_path / "nova_school_server" / "seccomp_profiles" / "container-denylist.json")
        if not profile_path.exists():
            profile_path = Path(__file__).resolve().parent / "seccomp_profiles" / "container-denylist.json"
        if not profile_path.exists():
            return None
        return resolve_seccomp_profile_option(profile_path, runtime_name)

    @staticmethod
    def _scheduler_notes(lease: SchedulerLease | None) -> list[str]:
        if lease is None:
            return []
        notes = [f"Run-Scheduler aktiv (Prioritaet: {lease.role}, Wartezeit: {lease.waited_ms} ms)."]
        if lease.queue_position > 1 or lease.waited_ms > 0:
            notes.append(f"Ausfuehrung wurde fair eingeordnet (erste Queue-Position: {lease.queue_position}).")
        return notes

    @staticmethod
    def _default_filename(language: str) -> str:
        return {"python": "snippet.py", "javascript": "snippet.js", "cpp": "snippet.cpp", "java": "Main.java", "rust": "snippet.rs", "html": "snippet.html", "node": "snippet.js", "npm": "package.json"}.get(language, "snippet.txt")

    def _execute_raw(self, command: list[str], cwd: Path, stdin_text: str, env: dict[str, str], *, timeout_seconds: int | None = None) -> "_RawResult":
        started_at = time.perf_counter()
        try:
            completed = subprocess.run(
                command,
                cwd=str(cwd),
                input=stdin_text,
                capture_output=True,
                text=True,
                timeout=timeout_seconds if timeout_seconds is not None else self.config.run_timeout_seconds,
                env=env,
                shell=False,
            )
            return _RawResult(completed.stdout, completed.stderr, completed.returncode, int((time.perf_counter() - started_at) * 1000))
        except subprocess.TimeoutExpired as exc:
            return _RawResult(exc.stdout or "", (exc.stderr or "") + "\nZeitlimit erreicht.", 124, int((time.perf_counter() - started_at) * 1000))
        except FileNotFoundError as exc:
            return _RawResult("", str(exc), 127, int((time.perf_counter() - started_at) * 1000))

    def _container_runtime_error_message(self, runtime_executable: str, image: str, raw_error: str) -> str:
        runtime_name = Path(runtime_executable).name or str(runtime_executable)
        message = str(raw_error or "").strip()
        lower = message.lower()
        if "zeitlimit erreicht" in lower or "timed out" in lower or "timeout" in lower:
            return (
                "Die Container-Runtime antwortet auf diesem Rechner nicht rechtzeitig und haengt wahrscheinlich intern.\n"
                "Der Docker-/Podman-Healthcheck ist bereits vor dem eigentlichen Schuelerprogramm ins Timeout gelaufen.\n\n"
                "So behebst du das:\n"
                "1. Docker Desktop oder Podman komplett neu starten\n"
                "2. pruefen, dass die Runtime danach wieder auf `docker info` oder `podman info` antwortet\n"
                "3. den Nova School Server danach neu starten\n\n"
                "Fuer den stabilen Schulbetrieb ist ein Linux-Worker oder ein kompletter Linux-Server die bessere Zielarchitektur.\n\n"
                f"Geplantes Image: {image}\n"
                f"Originalfehler: {message}"
            )
        if "500 internal server error" in lower or "request returned 500 internal server error" in lower:
            return (
                "Die Container-Runtime Docker Desktop antwortet auf diesem Rechner aktuell fehlerhaft oder haengt intern.\n"
                "Die Docker-API liefert einen 500-Fehler statt einen gueltigen Container-Start.\n\n"
                "So behebst du das:\n"
                "1. Docker Desktop komplett beenden\n"
                "2. Docker Desktop neu starten\n"
                "3. pruefen, dass Linux-Container aktiv sind\n"
                "4. den Nova School Server danach neu starten\n\n"
                "Wenn das in der Schule dauerhaft stabil laufen soll, sollte die Ausfuehrung auf einen Linux-Worker oder Linux-Server verlagert werden.\n\n"
                f"Geplantes Image: {image}\n"
                f"Originalfehler: {message}"
            )
        if "dockerdesktoplinuxengine" in lower or "failed to connect to the docker api" in lower:
            return (
                "Die Container-Runtime Docker ist auf diesem Rechner aktuell nicht betriebsbereit.\n"
                "Docker Desktop bzw. die Linux-Container-Engine wurde nicht gefunden oder laeuft nicht.\n\n"
                "So behebst du das:\n"
                "1. Docker Desktop starten\n"
                "2. pruefen, dass Linux-Container aktiv sind\n"
                "3. den Nova School Server danach neu starten\n\n"
                f"Geplantes Image: {image}\n"
                f"Originalfehler: {message}"
            )
        if "cannot connect to the docker daemon" in lower or "is the docker daemon running" in lower:
            return (
                "Die Container-Runtime Docker ist installiert, aber der Docker-Daemon laeuft nicht.\n"
                "Bitte den Docker-Dienst bzw. Docker Desktop starten und den Nova School Server neu ausfuehren.\n\n"
                f"Geplantes Image: {image}\n"
                f"Originalfehler: {message}"
            )
        if "no such image" in lower or "unable to find image" in lower:
            return (
                "Das benoetigte Container-Image ist lokal nicht verfuegbar.\n"
                "Bitte die Runtime starten und das Image einmal laden oder im Admin-Bereich ein vorhandenes Image konfigurieren.\n\n"
                f"Geplantes Image: {image}\n"
                f"Originalfehler: {message}"
            )
        if "system cannot find the file specified" in lower or "no such file or directory" in lower:
            return (
                f"Die konfigurierte Container-Runtime '{runtime_name}' wurde auf dem Server nicht gefunden.\n"
                "Bitte Docker oder Podman installieren bzw. die Runtime-Einstellung im Admin-Bereich korrigieren.\n\n"
                f"Geplantes Image: {image}\n"
                f"Originalfehler: {message or runtime_name}"
            )
        return message or f"Container-Image nicht verfuegbar oder Runtime nicht gestartet: {image}"

    def _container_runtime_health(self, runtime_executable: str, image: str) -> tuple[bool, str]:
        runtime_name = str(Path(runtime_executable).name or runtime_executable).lower()
        now = time.time()
        cached = self._container_runtime_health_cache.get(runtime_name)
        if cached and cached[0] > now:
            return cached[1], cached[2]
        command = [runtime_executable, "info", "--format", "{{.ServerVersion}}|{{.OSType}}"]
        result = self._execute_raw(command, self.config.base_path, "", dict(os.environ), timeout_seconds=6)
        if result.returncode == 0:
            payload = (now + 10.0, True, "")
            self._container_runtime_health_cache[runtime_name] = payload
            return True, ""
        message = self._container_runtime_error_message(runtime_executable, image, result.stderr or result.stdout or f"Runtime-Healthcheck fehlgeschlagen (Code {result.returncode}).")
        payload = (now + 5.0, False, message)
        self._container_runtime_health_cache[runtime_name] = payload
        return False, message


@dataclass(slots=True)
class _RawResult:
    stdout: str
    stderr: str
    returncode: int
    duration_ms: int
    command: list[str] | None = None

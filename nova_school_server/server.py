from __future__ import annotations

import atexit
import json
import mimetypes
import socket
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, unquote, urlparse

from .auth import AuthService, SessionContext
from .collaboration import NotebookCollaborationService
from .code_runner import CodeRunner
from .config import (
    ServerConfig,
    active_runtime_config,
    runtime_config_requires_restart,
    save_server_config_payload,
    stored_runtime_config,
)
from .curriculum import CurriculumService
from .database import SchoolRepository
from .deployments import DeploymentService
from .docs_catalog import DocumentationCatalog
from .distributed import DistributedPlaygroundService
from .lms_client import LMStudioService, normalize_lmstudio_base_url
from .mentor import SocraticMentorService
from .nova_bridge import load_nova_bridge
from .permissions import permission_catalog
from .realtime import RealtimeService, upgrade_websocket
from .reviews import ReviewService
from .reference_library import ReferenceLibraryService
from .seed import bootstrap_application
from .templates import PROJECT_TEMPLATES
from .user_admin import UserAdministrationService
from .wiki_manual import WikiManualService
from .workspace import WorkspaceManager, slugify


COOKIE_NAME = "nova_school_token"
ADMIN_SETTING_KEYS = [
    "school_name",
    "server_public_host",
    "certificate_logo_path",
    "certificate_signatory_name",
    "certificate_signatory_title",
    "web_proxy_url",
    "web_proxy_no_proxy",
    "web_proxy_required",
    "lmstudio_base_url",
    "lmstudio_model",
    "runner_backend",
    "unsafe_process_backend_enabled",
    "playground_dispatch_mode",
    "container_runtime",
    "container_oci_runtime",
    "container_memory_limit",
    "container_cpu_limit",
    "container_pids_limit",
    "container_file_size_limit_kb",
    "container_nofile_limit",
    "container_tmpfs_limit",
    "container_seccomp_enabled",
    "container_seccomp_profile",
    "container_image_python",
    "container_image_node",
    "container_image_cpp",
    "container_image_java",
    "container_image_rust",
    "scheduler_max_concurrent_global",
    "scheduler_max_concurrent_student",
    "scheduler_max_concurrent_teacher",
    "scheduler_max_concurrent_admin",
]
RUNTIME_FILE_CONFIG_KEYS = [
    "host",
    "port",
    "session_ttl_seconds",
    "run_timeout_seconds",
    "live_run_timeout_seconds",
    "tenant_id",
    "nova_shell_path",
]


class NovaSchoolApplication:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config
        bridge = load_nova_bridge(config.nova_shell_path)
        self.security = bridge.SecurityPlane(config.base_path)
        self.tool_sandbox = bridge.ToolSandbox()
        self.repository = SchoolRepository(config.database_path)
        self.auth = AuthService(self.repository, self.security, config.tenant_id, config.session_ttl_seconds)
        self.docs = DocumentationCatalog(config.docs_path)
        self.wiki_manual = WikiManualService(config.base_path / "wiki")
        self.workspace = WorkspaceManager(config)
        self.user_admin = UserAdministrationService(self.repository)
        self.runner = CodeRunner(config, self.tool_sandbox, self.workspace, self.repository)
        self.lmstudio = LMStudioService(bridge.NovaAIProviderRuntime, self.repository, config)
        self.collaboration = NotebookCollaborationService(self.repository, self.workspace)
        self.mentor = SocraticMentorService(self.repository, self.lmstudio)
        self.playground = DistributedPlaygroundService(self.repository, self.workspace, self.security, config, runner=self.runner)
        self.worker_dispatch = self.playground.dispatch
        self.reviews = ReviewService(self.repository, self.security, self.workspace, config.tenant_id, config.data_path / "review_submissions")
        self.deployments = DeploymentService(self.repository, self.workspace, self.security, config)
        self.curriculum = CurriculumService(self.repository)
        self.reference_library = ReferenceLibraryService(
            config.data_path / "reference_library",
            docs_source_root=config.base_path / "docs" / "nova_school",
        )
        self.realtime = RealtimeService(self)
        self.seed_info = bootstrap_application(self.repository, self.auth, self.docs, self.workspace)

    def close(self) -> None:
        self.realtime.close()
        self.playground.close()
        self.repository.close()
        self.security.close()

    def session_from_token(self, token: str | None) -> SessionContext | None:
        if not token:
            return None
        return self.auth.session_from_token(token)

    def accessible_projects(self, session: SessionContext) -> list[dict[str, Any]]:
        return [
            self.project_payload(project)
            for project in self.repository.list_accessible_projects(session.username, session.role, session.group_ids)
        ]

    def project_payload(self, project: dict[str, Any]) -> dict[str, Any]:
        payload = dict(project)
        payload["workspace_root"] = str(self.workspace.project_root(project))
        payload["owner_label"] = project["owner_key"]
        return payload

    def rooms_for(self, session: SessionContext, projects: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
        rooms = [{"key": "lounge:school", "label": "Schul-Lounge", "kind": "lounge"}]
        groups = self.repository.list_groups() if session.is_teacher else session.groups
        for group in groups:
            rooms.append({"key": f"group:{group['group_id']}", "label": f"Gruppe: {group['display_name']}", "kind": "group"})
        for project in (projects or self.accessible_projects(session)):
            rooms.append({"key": f"project:{project['project_id']}", "label": f"Projekt: {project['name']}", "kind": "project"})
        return rooms

    def public_settings(self, session: SessionContext) -> dict[str, Any]:
        settings = {
            "school_name": self.repository.get_setting("school_name", self.config.school_name),
            "lmstudio_model": self.repository.get_setting("lmstudio_model", ""),
        }
        if session.is_teacher:
            settings["lmstudio_base_url"] = normalize_lmstudio_base_url(self.repository.get_setting("lmstudio_base_url", "http://127.0.0.1:1234/v1"))
        return settings

    def bootstrap_payload(self, session: SessionContext) -> dict[str, Any]:
        projects = self.accessible_projects(session)
        ai_status = {"enabled": bool(session.permissions.get("ai.use", False))}
        if session.permissions.get("ai.use", False) or session.is_teacher:
            ai_status = self.lmstudio.status()
        return {
            "session": session.to_dict(),
            "projects": projects,
            "docs": self.docs.list_docs(),
            "rooms": self.rooms_for(session, projects),
            "permissions_catalog": permission_catalog(),
            "settings": self.public_settings(session),
            "templates": self.template_catalog(),
            "lmstudio": ai_status,
        }

    def template_catalog(self) -> list[dict[str, Any]]:
        return [
            {
                "key": key,
                "label": value["label"],
                "runtime": value["runtime"],
                "main_file": value["main_file"],
            }
            for key, value in PROJECT_TEMPLATES.items()
        ]

    def get_project_for_session(self, session: SessionContext, project_id: str) -> dict[str, Any]:
        project = self.repository.get_project(project_id)
        if project is None:
            raise FileNotFoundError("Projekt nicht gefunden.")
        if self.can_access_project(session, project):
            return project
        raise PermissionError("Kein Zugriff auf dieses Projekt.")

    def can_access_project(self, session: SessionContext, project: dict[str, Any]) -> bool:
        if session.is_teacher:
            return True
        if project["owner_type"] == "user":
            return project["owner_key"] == session.username
        if project["owner_type"] == "group":
            return project["owner_key"] in session.group_ids and session.permissions.get("workspace.group", False)
        return False

    def can_access_room(self, session: SessionContext, room_key: str) -> bool:
        if not session.permissions.get("chat.use", False) and not session.is_teacher:
            return False
        if room_key == "lounge:school":
            return True
        if room_key.startswith("group:"):
            group_id = room_key.split(":", 1)[1]
            return session.is_teacher or group_id in session.group_ids
        if room_key.startswith("project:"):
            project = self.repository.get_project(room_key.split(":", 1)[1])
            return project is not None and self.can_access_project(session, project)
        return False

    def admin_overview(self) -> dict[str, Any]:
        settings = self.repository.list_settings()
        if "lmstudio_base_url" in settings:
            settings["lmstudio_base_url"] = normalize_lmstudio_base_url(settings.get("lmstudio_base_url"))
        return {
            "users": self.user_admin.sanitize_users(self.repository.list_users()),
            "groups": self.repository.list_groups(),
            "memberships": self.repository.list_memberships(),
            "projects": [self.project_payload(project) for project in self.repository.list_projects()],
            "settings": settings,
            "reviews": self.reviews.dashboard(type("AdminSession", (), {"username": "admin", "is_teacher": True})()),
            "artifacts": self.deployments.list_artifacts(type("AdminSession", (), {"username": "admin", "is_teacher": True})()),
            "runtime": {
                "config": self.runtime_config_payload(),
                "security": self.security.snapshot(),
                "tool_sandbox": self.tool_sandbox.snapshot(),
            },
            "workers": self.worker_dispatch.list_workers(),
            "dispatch_jobs": self.repository.list_dispatch_jobs(),
            "curriculum": self.curriculum.dashboard(type("AdminSession", (), {"username": "admin", "permissions": {"curriculum.use": True, "curriculum.manage": True}, "is_teacher": True, "group_ids": []})()),
        }

    def runtime_config_payload(self) -> dict[str, Any]:
        active = active_runtime_config(self.config)
        stored = stored_runtime_config(self.config.base_path, self.config)
        local_url = f"http://127.0.0.1:{self.config.port}"
        if self.config.host in {"0.0.0.0", "::"}:
            lan_ip = _guess_lan_ipv4()
            lan_url = f"http://{lan_ip}:{self.config.port}" if lan_ip else ""
        else:
            lan_url = f"http://{self.config.host}:{self.config.port}"
        return {
            "active": active,
            "stored": stored,
            "restart_required": runtime_config_requires_restart(active, stored),
            "paths": {
                "config_path": str(self.config.base_path / "server_config.json"),
                "database_path": str(self.config.database_path),
                "data_path": str(self.config.data_path),
                "docs_path": str(self.config.docs_path),
                "users_workspace_path": str(self.config.users_workspace_path),
                "groups_workspace_path": str(self.config.groups_workspace_path),
                "nova_shell_path": str(self.config.nova_shell_path or ""),
            },
            "urls": {
                "local_url": local_url,
                "lan_url": lan_url,
            },
        }

    def server_settings_overview(self) -> dict[str, Any]:
        settings = self.repository.list_settings()
        if "lmstudio_base_url" in settings:
            settings["lmstudio_base_url"] = normalize_lmstudio_base_url(settings.get("lmstudio_base_url"))
        return {
            "settings": settings,
            "runtime": self.runtime_config_payload(),
        }


def create_application(config: ServerConfig) -> NovaSchoolApplication:
    application = NovaSchoolApplication(config)
    atexit.register(application.close)
    return application


class NovaSchoolRequestHandler(BaseHTTPRequestHandler):
    application: NovaSchoolApplication

    def do_GET(self) -> None:
        self._dispatch("GET")

    def do_POST(self) -> None:
        self._dispatch("POST")

    def do_PUT(self) -> None:
        self._dispatch("PUT")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        setattr(self, "_websocket_upgraded", False)
        try:
            if path.startswith("/ws/") and method == "GET":
                self._serve_websocket(path)
                return
            if path.startswith("/static/") and method == "GET":
                self._serve_file(self.application.config.static_path / path.removeprefix("/static/"))
                return
            if path.startswith("/share/") and method == "GET":
                self._serve_share(path)
                return
            if path.startswith("/download/") and method == "GET":
                self._serve_download(path)
                return
            if path.startswith("/preview/") and method == "GET":
                self._serve_preview(path)
                return
            if path == "/reference" and method == "GET":
                self._serve_reference(parsed)
                return
            if path == "/certificate/verify" and method == "GET":
                self._serve_certificate_verify(parsed)
                return
            if path.startswith("/reference/assets/") and method == "GET":
                self._serve_reference_asset(path)
                return
            if path == "/manual" and method == "GET":
                self._serve_manual(parsed)
                return
            if path.startswith("/api/"):
                self._handle_api(method, path, parsed)
                return
            if method == "GET":
                self._serve_file(self.application.config.static_path / "index.html", content_type="text/html; charset=utf-8")
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        except PermissionError as exc:
            if getattr(self, "_websocket_upgraded", False):
                return
            self._send_json(HTTPStatus.FORBIDDEN, {"error": str(exc)})
        except FileNotFoundError as exc:
            if getattr(self, "_websocket_upgraded", False):
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except ValueError as exc:
            if getattr(self, "_websocket_upgraded", False):
                return
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:  # pragma: no cover
            if getattr(self, "_websocket_upgraded", False):
                return
            self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})

    def _handle_api(self, method: str, path: str, parsed: Any) -> None:
        segments = [segment for segment in path.split("/") if segment]

        if method == "GET" and path == "/api/session":
            session = self._current_session()
            self._send_json(HTTPStatus.OK, {"authenticated": bool(session), "session": session.to_dict() if session else None})
            return

        if method == "POST" and path == "/api/login":
            body = self._read_json_body()
            token, session = self.application.auth.login(str(body.get("username", "")), str(body.get("password", "")))
            self.application.repository.add_audit(session.username, "login", "session", session.token_id, {})
            self._send_json(
                HTTPStatus.OK,
                {"ok": True, "bootstrap": self.application.bootstrap_payload(session)},
                cookies=[self._cookie_header(token)],
            )
            return

        if method == "POST" and path == "/api/logout":
            session = self._require_session()
            self.application.auth.logout(session.token_id)
            self.application.repository.add_audit(session.username, "logout", "session", session.token_id, {})
            self._send_json(HTTPStatus.OK, {"ok": True}, cookies=[self._clear_cookie_header()])
            return

        if path.startswith("/api/worker/"):
            self._handle_worker_api(method, path, segments)
            return

        session = self._require_session()

        if method == "GET" and path == "/api/bootstrap":
            self._send_json(HTTPStatus.OK, self.application.bootstrap_payload(session))
            return

        if method == "GET" and path == "/api/docs":
            self._require_permission(session, "docs.read")
            self._send_json(HTTPStatus.OK, {"docs": self.application.docs.list_docs()})
            return

        if method == "GET" and len(segments) == 3 and segments[:2] == ["api", "docs"]:
            self._require_permission(session, "docs.read")
            self._send_json(HTTPStatus.OK, self.application.docs.get_doc(segments[2]))
            return

        if method == "GET" and path == "/api/chat/rooms":
            self._require_permission(session, "chat.use")
            self._send_json(HTTPStatus.OK, {"rooms": self.application.rooms_for(session)})
            return

        if method == "GET" and path == "/api/chat/messages":
            self._require_permission(session, "chat.use")
            query = parse_qs(parsed.query)
            room_key = str(query.get("room_key", [""])[0])
            if not self.application.can_access_room(session, room_key):
                raise PermissionError("Kein Zugriff auf diesen Chatraum.")
            since = query.get("since", [None])[0]
            since_value = float(since) if since not in {None, ""} else None
            mute = self.application.repository.get_active_mute(room_key, session.username)
            self._send_json(
                HTTPStatus.OK,
                {"messages": self.application.repository.list_chat_messages(room_key, since_value), "mute": mute},
            )
            return

        if method == "POST" and path == "/api/chat/messages":
            self._require_permission(session, "chat.use")
            body = self._read_json_body()
            room_key = str(body.get("room_key") or "")
            message = str(body.get("message") or "").strip()
            if not message:
                raise ValueError("Nachricht darf nicht leer sein.")
            if not self.application.can_access_room(session, room_key):
                raise PermissionError("Kein Zugriff auf diesen Chatraum.")
            mute = self.application.repository.get_active_mute(room_key, session.username)
            if mute and not session.permissions.get("teacher.chat.moderate", False):
                raise PermissionError(f"Du bist bis {mute['muted_until']:.0f} stummgeschaltet.")
            payload = self.application.repository.add_chat_message(room_key, session.username, session.user["display_name"], message[:2000])
            self.application.repository.add_audit(session.username, "chat.message", "room", room_key, {"message_id": payload["message_id"]})
            self._send_json(HTTPStatus.OK, payload)
            return

        if method == "GET" and path == "/api/projects":
            self._send_json(HTTPStatus.OK, {"projects": self.application.accessible_projects(session)})
            return

        if method == "POST" and path == "/api/projects":
            self._require_permission(session, "project.create")
            body = self._read_json_body()
            template_key = str(body.get("template") or "")
            if template_key not in PROJECT_TEMPLATES:
                raise ValueError("Unbekanntes Projekt-Template.")
            owner_type = str(body.get("owner_type") or "user")
            if owner_type == "user":
                self._require_permission(session, "workspace.personal")
                owner_key = session.username
            elif owner_type == "group":
                self._require_permission(session, "workspace.group")
                owner_key = str(body.get("group_id") or "")
                if not owner_key:
                    raise ValueError("Gruppen-ID fehlt.")
                if owner_key not in session.group_ids and not session.is_teacher:
                    raise PermissionError("Kein Zugriff auf diese Gruppe.")
            else:
                raise ValueError("owner_type muss `user` oder `group` sein.")

            name = str(body.get("name") or "").strip()
            if not name:
                raise ValueError("Projektname fehlt.")
            description = str(body.get("description") or "").strip()
            template = PROJECT_TEMPLATES[template_key]
            slug = slugify(name)
            if self.application.repository.find_project_by_owner_and_slug(owner_type, owner_key, slug) is not None:
                raise ValueError("Projekt mit diesem Namen existiert bereits.")
            project = self.application.repository.create_project(
                owner_type=owner_type,
                owner_key=owner_key,
                name=name,
                slug=slug,
                template=template_key,
                runtime=str(template["runtime"]),
                main_file=str(template["main_file"]),
                description=description,
                created_by=session.username,
            )
            self.application.workspace.materialize_project(project)
            self.application.repository.add_audit(session.username, "project.create", "project", project["project_id"], {"template": template_key})
            self._send_json(HTTPStatus.OK, self.application.project_payload(project))
            return

        if len(segments) >= 3 and segments[:2] == ["api", "projects"]:
            project = self.application.get_project_for_session(session, segments[2])
            if method == "GET" and len(segments) == 3:
                self._send_json(HTTPStatus.OK, self.application.project_payload(project))
                return
            if method == "GET" and len(segments) == 4 and segments[3] == "tree":
                self._send_json(HTTPStatus.OK, {"entries": self.application.workspace.list_tree(project)})
                return
            if len(segments) == 4 and segments[3] == "file":
                if method == "GET":
                    query = parse_qs(parsed.query)
                    relative_path = str(query.get("path", [project["main_file"]])[0])
                    self._send_json(HTTPStatus.OK, self.application.workspace.read_file(project, relative_path))
                    return
                if method == "PUT":
                    self._require_permission(session, "files.write")
                    body = self._read_json_body()
                    relative_path = str(body.get("path") or "")
                    content = str(body.get("content") or "")
                    if not relative_path:
                        raise ValueError("Dateipfad fehlt.")
                    payload = self.application.workspace.write_file(project, relative_path, content)
                    self.application.repository.add_audit(session.username, "file.write", "project", project["project_id"], {"path": relative_path})
                    self._send_json(HTTPStatus.OK, payload)
                    return
            if len(segments) == 4 and segments[3] == "notebook":
                if method == "GET":
                    self._send_json(HTTPStatus.OK, {"cells": self.application.workspace.load_notebook(project)})
                    return
                if method == "PUT":
                    self._require_permission(session, "files.write")
                    body = self._read_json_body()
                    cells = list(body.get("cells") or [])
                    self._send_json(HTTPStatus.OK, {"cells": self.application.workspace.save_notebook(project, cells)})
                    return
            if len(segments) == 5 and segments[3] == "collab" and segments[4] == "notebook":
                self._require_permission(session, "notebook.collaborate")
                if method == "GET":
                    self._send_json(HTTPStatus.OK, self.application.collaboration.snapshot(project))
                    return
                if method == "PUT":
                    body = self._read_json_body()
                    payload = self.application.collaboration.sync(
                        session,
                        project,
                        list(body.get("cells") or []),
                        int(body.get("base_revision") or 0),
                        cursor=body.get("cursor") if isinstance(body.get("cursor"), dict) else None,
                    )
                    self._send_json(HTTPStatus.OK, payload)
                    return
            if method == "POST" and len(segments) == 5 and segments[3] == "collab" and segments[4] == "presence":
                self._require_permission(session, "notebook.collaborate")
                body = self._read_json_body()
                self._send_json(
                    HTTPStatus.OK,
                    {"presence": self.application.collaboration.heartbeat(session, project, body.get("cursor") if isinstance(body.get("cursor"), dict) else None)},
                )
                return
            if method == "POST" and len(segments) == 4 and segments[3] == "run":
                body = self._read_json_body()
                result = self.application.runner.run(session, project, body)
                self.application.repository.add_audit(
                    session.username,
                    "project.run",
                    "project",
                    project["project_id"],
                    {
                        "language": result["language"],
                        "returncode": result["returncode"],
                        "duration_ms": result["duration_ms"],
                        "command": result["command"],
                        "preview_path": result["preview_path"],
                    },
                )
                self._send_json(HTTPStatus.OK, result)
                return
            if len(segments) == 5 and segments[3] == "mentor" and segments[4] == "thread" and method == "GET":
                self._require_permission(session, "mentor.use")
                self._require_permission(session, "ai.use")
                self._send_json(HTTPStatus.OK, {"thread": self.application.mentor.thread(session, project)})
                return
            if len(segments) == 5 and segments[3] == "mentor" and segments[4] == "ask" and method == "POST":
                self._require_permission(session, "mentor.use")
                self._require_permission(session, "ai.use")
                body = self._read_json_body()
                prompt = str(body.get("prompt") or "").strip()
                if not prompt:
                    raise ValueError("Mentor-Prompt fehlt.")
                self._send_json(
                    HTTPStatus.OK,
                    self.application.mentor.ask(
                        session,
                        project,
                        prompt=prompt,
                        code=str(body.get("code") or ""),
                        path_hint=str(body.get("path") or ""),
                        run_output=str(body.get("run_output") or ""),
                        model=str(body.get("model") or "").strip() or None,
                    ),
                )
                return
            if len(segments) == 4 and segments[3] == "playground" and method == "GET":
                self._require_permission(session, "playground.manage")
                self._send_json(HTTPStatus.OK, self.application.playground.status(project))
                return
            if len(segments) == 5 and segments[3] == "playground" and segments[4] == "start" and method == "POST":
                self._require_permission(session, "playground.manage")
                body = self._read_json_body()
                names = [str(item) for item in list(body.get("services") or []) if str(item).strip()]
                self._send_json(HTTPStatus.OK, self.application.playground.start(session, project, service_names=names or None))
                return
            if len(segments) == 5 and segments[3] == "playground" and segments[4] == "stop" and method == "POST":
                self._require_permission(session, "playground.manage")
                body = self._read_json_body()
                names = [str(item) for item in list(body.get("services") or []) if str(item).strip()]
                self._send_json(HTTPStatus.OK, self.application.playground.stop(session, project, service_names=names or None))
                return
            if len(segments) == 5 and segments[3] == "reviews" and segments[4] == "submit" and method == "POST":
                self._require_permission(session, "review.use")
                submission = self.application.reviews.submit(session, project)
                self.application.repository.add_audit(session.username, "review.submit", "project", project["project_id"], {"submission_id": submission["submission_id"]})
                self._send_json(HTTPStatus.OK, submission)
                return
            if len(segments) == 5 and segments[3] == "deploy" and segments[4] == "share" and method == "POST":
                self._require_permission(session, "deploy.use")
                artifact = self.application.deployments.create_share(session, project)
                self.application.repository.add_audit(session.username, "deploy.share", "project", project["project_id"], {"artifact_id": artifact["artifact_id"]})
                self._send_json(HTTPStatus.OK, artifact)
                return
            if len(segments) == 5 and segments[3] == "deploy" and segments[4] == "export" and method == "POST":
                self._require_permission(session, "deploy.use")
                artifact = self.application.deployments.create_export(session, project)
                self.application.repository.add_audit(session.username, "deploy.export", "project", project["project_id"], {"artifact_id": artifact["artifact_id"]})
                self._send_json(HTTPStatus.OK, artifact)
                return

        if method == "GET" and path == "/api/assistant/status":
            self._require_permission(session, "ai.use")
            self._send_json(HTTPStatus.OK, self.application.lmstudio.status())
            return

        if method == "POST" and path == "/api/assistant/chat":
            self._require_permission(session, "ai.use")
            body = self._read_json_body()
            prompt = str(body.get("prompt") or "").strip()
            if not prompt:
                raise ValueError("Prompt fehlt.")
            context_bits = [prompt]
            code = str(body.get("code") or "").strip()
            if code:
                context_bits.append(f"Codekontext:\n```text\n{code}\n```")
            path_hint = str(body.get("path") or "").strip()
            if path_hint:
                context_bits.append(f"Aktive Datei: {path_hint}")
            payload = self.application.lmstudio.complete(
                "\n\n".join(context_bits),
                system_prompt="Du bist ein lokaler Codehelfer fuer einen Schulserver. Antworte knapp, konkret und sicherheitsbewusst.",
                model=str(body.get("model") or "").strip() or None,
            )
            self.application.repository.add_audit(session.username, "assistant.chat", "assistant", "lmstudio", {"model": payload["model"]})
            self._send_json(HTTPStatus.OK, payload)
            return

        if method == "GET" and path == "/api/admin/overview":
            self._require_permission(session, "admin.manage")
            self._send_json(HTTPStatus.OK, self.application.admin_overview())
            return

        if method == "GET" and path == "/api/server/settings":
            self._require_server_settings_access(session)
            self._send_json(HTTPStatus.OK, self.application.server_settings_overview())
            return

        if method == "GET" and path == "/api/curriculum/dashboard":
            self._require_permission(session, "curriculum.use")
            self._send_json(HTTPStatus.OK, self.application.curriculum.dashboard(session))
            return

        if method == "GET" and path == "/api/curriculum/attempts":
            self._require_permission(session, "curriculum.manage")
            query = parse_qs(parsed.query or "")
            course_id = str((query.get("course_id") or [""])[0] or "").strip()
            username = str((query.get("username") or [""])[0] or "").strip()
            if not course_id:
                raise ValueError("course_id fehlt.")
            if not username:
                raise ValueError("username fehlt.")
            self._send_json(HTTPStatus.OK, self.application.curriculum.attempt_history(course_id, username))
            return

        if method == "POST" and path == "/api/curriculum/catalog/save":
            self._require_permission(session, "curriculum.manage")
            body = self._read_json_body()
            payload = self.application.curriculum.save_custom_course(session, dict(body.get("course") or {}))
            self.application.repository.add_audit(
                session.username,
                "curriculum.catalog.save",
                "curriculum_course",
                str(payload["course_id"]),
                {"title": payload["title"], "is_custom": True},
            )
            self._send_json(HTTPStatus.OK, {"course": payload})
            return

        if method == "GET" and path == "/api/curriculum/certificate":
            self._require_permission(session, "curriculum.use")
            query = parse_qs(parsed.query or "")
            course_id = str((query.get("course_id") or [""])[0] or "").strip()
            if not course_id:
                raise ValueError("course_id fehlt.")
            certificate = self.application.curriculum.prepare_certificate_metadata(
                session.username,
                course_id=course_id,
                verification_url=self._certificate_verification_url(f"{course_id}:{session.username}"),
                signatory_name=str(self.application.repository.get_setting("certificate_signatory_name", "") or ""),
                signatory_title=str(self.application.repository.get_setting("certificate_signatory_title", "") or ""),
                logo_path=str(self.application.repository.get_setting("certificate_logo_path", "") or ""),
            )
            if certificate is None:
                raise FileNotFoundError("Fuer diesen Kurs liegt noch kein Zertifikat vor.")
            payload = self.application.curriculum.build_certificate_pdf(
                session,
                course_id=course_id,
                school_name=str(self.application.repository.get_setting("school_name", self.application.config.school_name) or self.application.config.school_name),
            )
            self.application.repository.add_audit(
                session.username,
                "curriculum.certificate.download",
                "curriculum_certificate",
                f"{course_id}:{session.username}",
                {"course_id": course_id},
            )
            self._send_bytes(
                HTTPStatus.OK,
                payload["content"],
                content_type=payload["content_type"],
                filename=payload["filename"],
            )
            return

        if method == "POST" and path == "/api/curriculum/submit":
            self._require_permission(session, "curriculum.use")
            body = self._read_json_body()
            course_id = str(body.get("course_id") or "").strip()
            module_id = str(body.get("module_id") or "").strip()
            assessment_kind = str(body.get("assessment_kind") or "module").strip()
            if not course_id:
                raise ValueError("course_id fehlt.")
            if assessment_kind == "module" and not module_id:
                raise ValueError("module_id fehlt.")
            payload = self.application.curriculum.submit_assessment(
                session,
                course_id=course_id,
                module_id=module_id or "__final__",
                assessment_kind=assessment_kind,
                answers=dict(body.get("answers") or {}),
            )
            self.application.repository.add_audit(
                session.username,
                "curriculum.submit",
                "curriculum",
                f"{course_id}:{module_id or assessment_kind}",
                {"assessment_kind": assessment_kind, "passed": payload["passed"], "score": payload["score"], "max_score": payload["max_score"]},
            )
            if payload.get("certificate"):
                self.application.repository.add_audit(
                    session.username,
                    "curriculum.certificate",
                    "curriculum_certificate",
                    f"{course_id}:{session.username}",
                    {"course_id": course_id, "score": payload["certificate"]["score"]},
                )
            self._send_json(HTTPStatus.OK, payload)
            return

        if method == "POST" and path == "/api/curriculum/releases":
            self._require_permission(session, "curriculum.manage")
            body = self._read_json_body()
            payload = self.application.curriculum.set_release(
                session,
                course_id=str(body.get("course_id") or "").strip(),
                scope_type=str(body.get("scope_type") or "").strip(),
                scope_key=str(body.get("scope_key") or "").strip(),
                enabled=bool(body.get("enabled", True)),
                note=str(body.get("note") or ""),
            )
            self.application.repository.add_audit(
                session.username,
                "curriculum.release",
                "curriculum_release",
                str(payload["release_id"]),
                {
                    "course_id": payload["course_id"],
                    "scope_type": payload["scope_type"],
                    "scope_key": payload["scope_key"],
                    "enabled": payload["enabled"],
                },
            )
            self._send_json(HTTPStatus.OK, payload)
            return

        if method == "GET" and path == "/api/admin/workers":
            self._require_permission(session, "admin.manage")
            self._send_json(
                HTTPStatus.OK,
                {
                    "workers": self.application.worker_dispatch.list_workers(),
                    "jobs": self.application.repository.list_dispatch_jobs(),
                },
            )
            return

        if method == "POST" and path == "/api/admin/workers/bootstrap":
            self._require_permission(session, "admin.manage")
            body = self._read_json_body()
            worker_id = str(body.get("worker_id") or "").strip()
            display_name = str(body.get("display_name") or worker_id).strip()
            if not worker_id:
                raise ValueError("worker_id fehlt.")
            payload = self.application.worker_dispatch.issue_bootstrap(
                worker_id=worker_id,
                display_name=display_name or worker_id,
                capabilities=[str(item) for item in list(body.get("capabilities") or []) if str(item).strip()],
                labels=dict(body.get("labels") or {}),
                metadata=dict(body.get("metadata") or {}),
            )
            self.application.repository.add_audit(
                session.username,
                "admin.worker.bootstrap",
                "worker",
                worker_id,
                {"display_name": display_name or worker_id},
            )
            self._send_json(HTTPStatus.OK, payload)
            return

        if method == "GET" and path == "/api/reviews/dashboard":
            self._require_permission(session, "review.use")
            self._send_json(HTTPStatus.OK, self.application.reviews.dashboard(session))
            return

        if method == "POST" and len(segments) == 3 and segments[:2] == ["api", "reviews"] and segments[2] == "feedback":
            self._require_permission(session, "review.use")
            body = self._read_json_body()
            assignment_id = str(body.get("assignment_id") or "").strip()
            if not assignment_id:
                raise ValueError("assignment_id fehlt.")
            payload = self.application.reviews.submit_feedback(session, assignment_id, dict(body.get("feedback") or {}))
            self.application.repository.add_audit(session.username, "review.feedback", "review_assignment", assignment_id, {})
            self._send_json(HTTPStatus.OK, payload)
            return

        if method == "GET" and path == "/api/deployments":
            self._require_permission(session, "deploy.use")
            self._send_json(HTTPStatus.OK, {"artifacts": self.application.deployments.list_artifacts(session)})
            return

        if method == "GET" and len(segments) == 5 and segments[:3] == ["api", "admin", "users"] and segments[4] == "audit":
            self._require_permission(session, "admin.manage")
            username = unquote(str(segments[3] or "")).strip()
            if not username:
                raise ValueError("username fehlt.")
            self._send_json(HTTPStatus.OK, {"entries": self.application.user_admin.audit_entries(username)})
            return

        if method == "POST" and path == "/api/admin/users":
            self._require_permission(session, "admin.manage")
            body = self._read_json_body()
            user = self.application.auth.create_user(
                username=str(body.get("username") or "").strip(),
                password=str(body.get("password") or "").strip(),
                role=str(body.get("role") or "student").strip(),
                display_name=str(body.get("display_name") or body.get("username") or "").strip(),
                permissions=body.get("permissions"),
            )
            self.application.workspace.ensure_profile_folder("user", user["username"])
            self.application.repository.add_audit(
                session.username,
                "admin.user.create",
                "user",
                user["username"],
                {
                    "display_name": user["display_name"],
                    "role": user["role"],
                    "status": user["status"],
                },
            )
            self._send_json(HTTPStatus.OK, self.application.user_admin.sanitize_user(user) or {})
            return

        if method == "POST" and path == "/api/admin/users/manage":
            self._require_permission(session, "admin.manage")
            body = self._read_json_body()
            username = str(body.get("username") or "").strip()
            if not username:
                raise ValueError("username fehlt.")
            payload = self.application.user_admin.update_user(
                actor_username=session.username,
                username=username,
                display_name=str(body.get("display_name") or "").strip(),
                role=str(body.get("role") or "").strip(),
                status=str(body.get("status") or "").strip(),
                password=str(body.get("password") or ""),
            )
            self._send_json(HTTPStatus.OK, payload)
            return

        if method == "POST" and path == "/api/admin/groups":
            self._require_permission(session, "admin.manage")
            body = self._read_json_body()
            raw_group = str(body.get("group_id") or body.get("display_name") or "").strip()
            if not raw_group:
                raise ValueError("Gruppen-ID oder Anzeigename fehlt.")
            group_id = slugify(raw_group)
            display_name = str(body.get("display_name") or raw_group).strip()
            if not display_name:
                raise ValueError("Gruppenname fehlt.")
            group = self.application.repository.create_group(
                group_id=group_id,
                display_name=display_name,
                description=str(body.get("description") or ""),
                permissions=body.get("permissions"),
            )
            self.application.workspace.ensure_profile_folder("group", group_id)
            self.application.repository.add_audit(session.username, "admin.group.create", "group", group_id, {})
            self._send_json(HTTPStatus.OK, group)
            return

        if method == "POST" and path == "/api/admin/memberships":
            self._require_permission(session, "admin.manage")
            body = self._read_json_body()
            username = str(body.get("username") or "").strip()
            group_id = str(body.get("group_id") or "").strip()
            action = str(body.get("action") or "add")
            if action == "remove":
                self.application.repository.remove_membership(username, group_id)
            else:
                self.application.repository.add_membership(username, group_id)
            self.application.repository.add_audit(session.username, "admin.membership.update", "group", group_id, {"username": username, "action": action})
            self._send_json(HTTPStatus.OK, {"ok": True})
            return

        if method == "POST" and path == "/api/admin/users/permissions":
            self._require_permission(session, "admin.manage")
            body = self._read_json_body()
            username = str(body.get("username") or "").strip()
            before = self.application.repository.get_user(username)
            updated = self.application.repository.update_user_permissions(username, dict(body.get("permissions") or {}))
            if updated is None:
                raise FileNotFoundError("Benutzer nicht gefunden.")
            self.application.repository.add_audit(
                session.username,
                "admin.user.permissions",
                "user",
                username,
                self.application.user_admin.permission_audit_payload(before, updated),
            )
            self._send_json(HTTPStatus.OK, self.application.user_admin.sanitize_user(updated) or {})
            return

        if method == "POST" and path == "/api/admin/groups/permissions":
            self._require_permission(session, "admin.manage")
            body = self._read_json_body()
            group_id = str(body.get("group_id") or "").strip()
            updated = self.application.repository.update_group_permissions(group_id, dict(body.get("permissions") or {}))
            self.application.repository.add_audit(session.username, "admin.group.permissions", "group", group_id, {})
            self._send_json(HTTPStatus.OK, updated)
            return

        if method == "POST" and path == "/api/admin/mutes":
            self._require_permission(session, "teacher.chat.moderate")
            body = self._read_json_body()
            payload = self.application.repository.set_mute(
                room_key=str(body.get("room_key") or "*"),
                target_username=str(body.get("target_username") or ""),
                duration_minutes=int(body.get("duration_minutes") or 10),
                reason=str(body.get("reason") or "Moderation"),
                created_by=session.username,
            )
            self.application.repository.add_audit(session.username, "admin.chat.mute", "room", payload["room_key"], payload)
            self._send_json(HTTPStatus.OK, payload)
            return

        if method == "POST" and path in {"/api/admin/settings", "/api/server/settings"}:
            self._require_server_settings_access(session)
            body = self._read_json_body()
            for key in ADMIN_SETTING_KEYS:
                if key in body:
                    value = body[key]
                    if key == "lmstudio_base_url":
                        value = normalize_lmstudio_base_url(value)
                    self.application.repository.put_setting(key, value)
            file_updates: dict[str, Any] = {}
            for key in RUNTIME_FILE_CONFIG_KEYS:
                if key not in body:
                    continue
                value = body[key]
                if key in {"port", "session_ttl_seconds", "run_timeout_seconds", "live_run_timeout_seconds"}:
                    value = int(value or 0)
                elif key == "nova_shell_path":
                    value = str(value or "").strip()
                else:
                    value = str(value or "").strip()
                file_updates[key] = value
            if file_updates:
                save_server_config_payload(self.application.config.base_path, file_updates)
            self.application.repository.add_audit(session.username, "admin.settings.update", "settings", "server", {})
            self._send_json(HTTPStatus.OK, self.application.server_settings_overview())
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _handle_worker_api(self, method: str, path: str, segments: list[str]) -> None:
        worker = self._require_worker()

        if method == "POST" and path == "/api/worker/heartbeat":
            body = self._read_json_body()
            payload = self.application.worker_dispatch.heartbeat(
                str(worker["worker_id"]),
                endpoint_url=str(body.get("endpoint_url") or ""),
                advertise_host=str(body.get("advertise_host") or ""),
                status=str(body.get("status") or "active"),
                metadata=dict(body.get("metadata") or {}),
                active_job_id=str(body.get("active_job_id") or ""),
            )
            self._send_json(HTTPStatus.OK, payload)
            return

        if method == "POST" and path == "/api/worker/jobs/claim":
            payload = self.application.worker_dispatch.claim_next_job(str(worker["worker_id"]))
            self._send_json(HTTPStatus.OK, {"job": payload})
            return

        if len(segments) >= 5 and segments[:3] == ["api", "worker", "jobs"]:
            job_id = str(segments[3] or "").strip()
            if not job_id:
                raise ValueError("job_id fehlt.")
            if method == "GET" and len(segments) == 5 and segments[4] == "artifact":
                target = self.application.worker_dispatch.resolve_job_artifact(job_id)
                self._serve_file(target, content_type="application/zip")
                return
            if method == "POST" and len(segments) == 5 and segments[4] == "log":
                body = self._read_json_body()
                payload = self.application.worker_dispatch.append_job_log(
                    str(worker["worker_id"]),
                    job_id,
                    str(body.get("chunk") or ""),
                )
                self._send_json(HTTPStatus.OK, payload)
                return
            if method == "POST" and len(segments) == 5 and segments[4] == "status":
                body = self._read_json_body()
                payload = self.application.worker_dispatch.update_job_status(
                    str(worker["worker_id"]),
                    job_id,
                    status=str(body.get("status") or "running"),
                    result=dict(body.get("result") or {}),
                    mark_started=bool(body.get("mark_started", False)),
                    mark_finished=bool(body.get("mark_finished", False)),
                    clear_stop_request=bool(body.get("clear_stop_request", False)),
                )
                self._send_json(HTTPStatus.OK, payload)
                return

        self._send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _serve_websocket(self, path: str) -> None:
        session = self._require_session()
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) == 3 and segments[:2] == ["ws", "projects"]:
            project = self.application.get_project_for_session(session, segments[2])
            connection = upgrade_websocket(self)
            self.application.realtime.handle_project_socket(connection, session, project)
            return
        raise FileNotFoundError("WebSocket-Endpunkt nicht gefunden.")

    def _serve_preview(self, path: str) -> None:
        session = self._require_session()
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) < 3:
            raise FileNotFoundError("Preview-Datei nicht gefunden.")
        project = self.application.get_project_for_session(session, segments[1])
        relative_path = unquote("/".join(segments[2:]))
        target = self.application.workspace.resolve_project_path(project, relative_path)
        self._serve_file(target)

    def _serve_share(self, path: str) -> None:
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) < 2:
            raise FileNotFoundError("Share nicht gefunden.")
        artifact_id = segments[1]
        relative_path = unquote("/".join(segments[2:])) if len(segments) > 2 else "index.html"
        target = self.application.deployments.resolve_share_path(artifact_id, relative_path)
        self._serve_file(target)

    def _serve_download(self, path: str) -> None:
        segments = [segment for segment in path.split("/") if segment]
        if len(segments) != 2:
            raise FileNotFoundError("Download nicht gefunden.")
        target = self.application.deployments.resolve_download_path(segments[1])
        self._serve_file(target, content_type="application/zip")

    def _serve_manual(self, parsed: Any) -> None:
        session = self._current_session()
        if session is None:
            self._redirect("/")
            return
        query = parse_qs(parsed.query or "")
        scope = str((query.get("scope") or [""])[0] or "").strip() or None
        page = str((query.get("page") or [""])[0] or "").strip() or None
        payload = self.application.wiki_manual.render_page(session, requested_scope=scope, requested_page=page)
        self._send_html(HTTPStatus.OK, payload)

    def _serve_reference(self, parsed: Any) -> None:
        session = self._current_session()
        if session is None:
            self._redirect("/")
            return
        self._require_permission(session, "docs.read")
        query = parse_qs(parsed.query or "")
        area = str((query.get("area") or [""])[0] or "").strip() or None
        doc = str((query.get("doc") or [""])[0] or "").strip() or None
        search = str((query.get("q") or [""])[0] or "").strip()
        payload = self.application.reference_library.render_portal(area=area, doc_id=doc, query=search)
        self._send_html(HTTPStatus.OK, payload)

    def _serve_certificate_verify(self, parsed: Any) -> None:
        query = parse_qs(parsed.query or "")
        certificate_id = str((query.get("certificate_id") or query.get("code") or [""])[0] or "").strip()
        if not certificate_id:
            raise ValueError("certificate_id fehlt.")
        school_name = str(self.application.repository.get_setting("school_name", self.application.config.school_name) or self.application.config.school_name)
        payload = self.application.curriculum.render_certificate_verification_page(certificate_id, school_name)
        self._send_html(HTTPStatus.OK, payload)

    def _serve_reference_asset(self, path: str) -> None:
        session = self._require_session()
        self._require_permission(session, "docs.read")
        segments = [unquote(segment) for segment in path.split("/") if segment]
        if len(segments) < 4:
            raise FileNotFoundError("Referenzdatei nicht gefunden.")
        area = str(segments[2] or "").strip()
        relative_path = "/".join(segments[3:])
        target = self.application.reference_library.resolve_asset(area, relative_path)
        self._serve_file(target)

    def _serve_file(self, path: Path, content_type: str | None = None) -> None:
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(str(path))
        mime = content_type or mimetypes.guess_type(str(path))[0] or "application/octet-stream"
        payload = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _current_session(self) -> SessionContext | None:
        token = self._token_from_request()
        return self.application.session_from_token(token)

    def _require_session(self) -> SessionContext:
        session = self._current_session()
        if session is None:
            raise PermissionError("Anmeldung erforderlich.")
        return session

    def _require_worker(self) -> dict[str, Any]:
        worker_id = str(self.headers.get("X-Nova-Worker-ID", "") or "").strip()
        token = self._token_from_request()
        timestamp = str(self.headers.get("X-Nova-Timestamp", "") or "").strip()
        nonce = str(self.headers.get("X-Nova-Nonce", "") or "").strip()
        signature = str(self.headers.get("X-Nova-Signature", "") or "").strip()
        if not worker_id or not token:
            raise PermissionError("Worker-Authentifizierung erforderlich.")
        return self.application.worker_dispatch.verify_worker_request(
            worker_id,
            token,
            method=self.command,
            path=urlparse(self.path).path,
            body=self._read_raw_body(),
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
        )

    @staticmethod
    def _require_permission(session: SessionContext, permission_key: str) -> None:
        if not session.permissions.get(permission_key, False):
            raise PermissionError(f"Recht fehlt: {permission_key}")

    @staticmethod
    def _can_manage_server_settings(session: SessionContext) -> bool:
        return session.is_teacher or session.permissions.get("admin.manage", False)

    def _require_server_settings_access(self, session: SessionContext) -> None:
        if not self._can_manage_server_settings(session):
            raise PermissionError("Recht fehlt: server.settings")

    def _certificate_verification_url(self, certificate_id: str) -> str:
        public_host = str(self.application.repository.get_setting("server_public_host", "") or "").strip()
        if public_host and not public_host.startswith(("http://", "https://")):
            public_host = f"http://{public_host}"
        base = public_host.rstrip("/") if public_host else f"http://127.0.0.1:{self.application.config.port}"
        return f"{base}/certificate/verify?certificate_id={quote(certificate_id)}"

    def _read_json_body(self) -> dict[str, Any]:
        payload = self._read_raw_body()
        if not payload:
            return {}
        return dict(json.loads(payload.decode("utf-8")))

    def _read_raw_body(self) -> bytes:
        cached = getattr(self, "_cached_request_body", None)
        if cached is not None:
            return cached
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            self._cached_request_body = b""
            return b""
        self._cached_request_body = self.rfile.read(length)
        return self._cached_request_body

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any], *, cookies: list[str] | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        for cookie in cookies or []:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def _send_bytes(
        self,
        status: HTTPStatus,
        payload: bytes,
        *,
        content_type: str = "application/octet-stream",
        filename: str | None = None,
    ) -> None:
        self.send_response(int(status))
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        if filename:
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.end_headers()
        self.wfile.write(payload)

    def _send_html(self, status: HTTPStatus, content: str) -> None:
        body = content.encode("utf-8")
        self.send_response(int(status))
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _token_from_request(self) -> str | None:
        cookie_header = self.headers.get("Cookie")
        if cookie_header:
            jar = SimpleCookie()
            jar.load(cookie_header)
            if COOKIE_NAME in jar:
                return jar[COOKIE_NAME].value
        auth_header = self.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[len("Bearer ") :].strip()
        return None

    @staticmethod
    def _cookie_header(token: str) -> str:
        return f"{COOKIE_NAME}={token}; HttpOnly; SameSite=Lax; Path=/"

    @staticmethod
    def _clear_cookie_header() -> str:
        return f"{COOKIE_NAME}=; Max-Age=0; HttpOnly; SameSite=Lax; Path=/"


def run_server(application: NovaSchoolApplication) -> None:
    class Handler(NovaSchoolRequestHandler):
        pass

    Handler.application = application

    server = ThreadingHTTPServer((application.config.host, application.config.port), Handler)
    seed_lines = ", ".join(f"{item['username']}/{item['password']}" for item in application.seed_info["seed_users"])
    bound_host = application.config.host
    bound_port = application.config.port
    if bound_host in {"0.0.0.0", "::"}:
        print(f"Nova School Server lauscht auf {bound_host}:{bound_port}")
        print(f"Lokal: http://127.0.0.1:{bound_port}")
        lan_ip = _guess_lan_ipv4()
        if lan_ip:
            print(f"Im LAN: http://{lan_ip}:{bound_port}")
        else:
            print(f"Im LAN: http://<server-ip>:{bound_port}")
    else:
        print(f"Nova School Server laeuft auf http://{bound_host}:{bound_port}")
    print(f"Demo-Logins: {seed_lines}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        application.close()


def _guess_lan_ipv4() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            ip = probe.getsockname()[0]
            return ip if ip and not ip.startswith("127.") else None
    except OSError:
        return None

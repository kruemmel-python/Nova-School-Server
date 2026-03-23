from __future__ import annotations

from typing import Any


PERMISSION_DEFINITIONS: tuple[dict[str, str], ...] = (
    {"key": "project.create", "label": "Projekte erstellen", "category": "Arbeitsbereich"},
    {"key": "workspace.personal", "label": "Eigene Profilordner nutzen", "category": "Arbeitsbereich"},
    {"key": "workspace.group", "label": "Gruppenordner nutzen", "category": "Arbeitsbereich"},
    {"key": "files.write", "label": "Dateien schreiben", "category": "Arbeitsbereich"},
    {"key": "notebook.collaborate", "label": "Live-Notebooks gemeinsam bearbeiten", "category": "Arbeitsbereich"},
    {"key": "chat.use", "label": "Im Editor chatten", "category": "Kommunikation"},
    {"key": "docs.read", "label": "Offline-Dokumentation lesen", "category": "Lernen"},
    {"key": "web.access", "label": "Webzugriff fuer Projekte", "category": "Netzwerk"},
    {"key": "ai.use", "label": "LM Studio Codehilfe", "category": "KI"},
    {"key": "mentor.use", "label": "Sokratischen KI-Mentor nutzen", "category": "KI"},
    {"key": "curriculum.use", "label": "Modullehrplaene lernen", "category": "Lernen"},
    {"key": "curriculum.manage", "label": "Modullehrplaene freischalten", "category": "Lernen"},
    {"key": "run.python", "label": "Python ausfuehren", "category": "Runner"},
    {"key": "run.javascript", "label": "JavaScript ausfuehren", "category": "Runner"},
    {"key": "run.cpp", "label": "C++ ausfuehren", "category": "Runner"},
    {"key": "run.java", "label": "Java ausfuehren", "category": "Runner"},
    {"key": "run.rust", "label": "Rust ausfuehren", "category": "Runner"},
    {"key": "run.html", "label": "HTML-Vorschau", "category": "Runner"},
    {"key": "run.node", "label": "Node.js ausfuehren", "category": "Runner"},
    {"key": "run.npm", "label": "npm-Kommandos ausfuehren", "category": "Runner"},
    {"key": "playground.manage", "label": "Distributed Playground steuern", "category": "Runner"},
    {"key": "review.use", "label": "Peer-Review nutzen", "category": "Lernen"},
    {"key": "deploy.use", "label": "Deployments und Shares nutzen", "category": "Deployment"},
    {"key": "teacher.chat.observe", "label": "Alle Chats einsehen", "category": "Moderation"},
    {"key": "teacher.chat.moderate", "label": "User stummschalten", "category": "Moderation"},
    {"key": "admin.manage", "label": "Server verwalten", "category": "Administration"},
)

PERMISSION_KEYS: tuple[str, ...] = tuple(item["key"] for item in PERMISSION_DEFINITIONS)
_ALL_TRUE = {key: True for key in PERMISSION_KEYS}

ROLE_DEFAULTS: dict[str, dict[str, bool]] = {
    "student": {
        "project.create": True,
        "workspace.personal": True,
        "workspace.group": True,
        "files.write": True,
        "notebook.collaborate": True,
        "chat.use": True,
        "docs.read": True,
        "web.access": False,
        "ai.use": True,
        "mentor.use": True,
        "curriculum.use": True,
        "curriculum.manage": False,
        "run.python": True,
        "run.javascript": True,
        "run.cpp": True,
        "run.java": True,
        "run.rust": True,
        "run.html": True,
        "run.node": True,
        "run.npm": True,
        "playground.manage": False,
        "review.use": True,
        "deploy.use": True,
        "teacher.chat.observe": False,
        "teacher.chat.moderate": False,
        "admin.manage": False,
    },
    "teacher": dict(_ALL_TRUE),
    "admin": dict(_ALL_TRUE),
}

ROLE_PERMISSION_FLOORS: dict[str, dict[str, bool]] = {
    "admin": dict(_ALL_TRUE),
}


def normalize_permission_overrides(raw: dict[str, Any] | None) -> dict[str, bool]:
    if not raw:
        return {}
    normalized: dict[str, bool] = {}
    for key, value in raw.items():
        if key not in PERMISSION_KEYS or value is None:
            continue
        normalized[key] = bool(value)
    return normalized


def resolve_permissions(role: str, group_overrides: list[dict[str, Any]] | None = None, user_overrides: dict[str, Any] | None = None) -> dict[str, bool]:
    effective = dict(ROLE_DEFAULTS.get(role, ROLE_DEFAULTS["student"]))
    for key in PERMISSION_KEYS:
        explicit_values = [
            bool(group[key])
            for group in (group_overrides or [])
            if isinstance(group, dict) and key in group and group[key] is not None
        ]
        if any(value is False for value in explicit_values):
            effective[key] = False
        elif any(value is True for value in explicit_values):
            effective[key] = True
    for key, value in normalize_permission_overrides(user_overrides).items():
        effective[key] = value
    for key, value in ROLE_PERMISSION_FLOORS.get(role, {}).items():
        if value:
            effective[key] = True
    return effective


def permission_catalog() -> list[dict[str, str]]:
    return [dict(item) for item in PERMISSION_DEFINITIONS]


def allowed_tool_names(permissions: dict[str, bool]) -> tuple[str, ...]:
    return tuple(sorted(key for key, value in permissions.items() if value))

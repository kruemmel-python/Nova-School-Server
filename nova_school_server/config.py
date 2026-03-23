from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

RUNTIME_FILE_CONFIG_KEYS = (
    "host",
    "port",
    "session_ttl_seconds",
    "run_timeout_seconds",
    "live_run_timeout_seconds",
    "tenant_id",
    "nova_shell_path",
)


@dataclass(slots=True)
class ServerConfig:
    base_path: Path
    data_path: Path
    docs_path: Path
    users_workspace_path: Path
    groups_workspace_path: Path
    static_path: Path
    database_path: Path
    host: str = "0.0.0.0"
    port: int = 8877
    session_ttl_seconds: int = 43_200
    run_timeout_seconds: int = 20
    live_run_timeout_seconds: int = 300
    tenant_id: str = "nova-school"
    school_name: str = "Nova School Server"
    nova_shell_path: Path | None = None

    @classmethod
    def from_base_path(cls, base_path: Path) -> "ServerConfig":
        base_path = base_path.resolve(strict=False)
        payload = load_server_config_payload(base_path)

        def env_or_payload(name: str, key: str, default: Any) -> Any:
            return os.environ.get(name) or payload.get(key) or default

        nova_shell_value = env_or_payload("NOVA_SHELL_PATH", "nova_shell_path", r"H:\Nova-shell-main")
        nova_shell_path = Path(str(nova_shell_value)).resolve(strict=False) if nova_shell_value else None

        data_path = base_path / "data"
        docs_path = data_path / "docs"
        workspaces_path = data_path / "workspaces"
        users_workspace_path = workspaces_path / "users"
        groups_workspace_path = workspaces_path / "groups"

        return cls(
            base_path=base_path,
            data_path=data_path,
            docs_path=docs_path,
            users_workspace_path=users_workspace_path,
            groups_workspace_path=groups_workspace_path,
            static_path=base_path / "nova_school_server" / "static",
            database_path=data_path / "school.db",
            host=str(env_or_payload("NOVA_SCHOOL_HOST", "host", "0.0.0.0")),
            port=int(env_or_payload("NOVA_SCHOOL_PORT", "port", 8877)),
            session_ttl_seconds=int(env_or_payload("NOVA_SCHOOL_SESSION_TTL", "session_ttl_seconds", 43_200)),
            run_timeout_seconds=int(env_or_payload("NOVA_SCHOOL_RUN_TIMEOUT", "run_timeout_seconds", 20)),
            live_run_timeout_seconds=int(env_or_payload("NOVA_SCHOOL_LIVE_RUN_TIMEOUT", "live_run_timeout_seconds", 300)),
            tenant_id=str(env_or_payload("NOVA_SCHOOL_TENANT", "tenant_id", "nova-school")),
            school_name=str(env_or_payload("NOVA_SCHOOL_NAME", "school_name", "Nova School Server")),
            nova_shell_path=nova_shell_path,
        )


def load_server_config_payload(base_path: Path) -> dict[str, Any]:
    path = Path(base_path).resolve(strict=False) / "server_config.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_server_config_payload(base_path: Path, updates: dict[str, Any]) -> dict[str, Any]:
    base_path = Path(base_path).resolve(strict=False)
    path = base_path / "server_config.json"
    payload = load_server_config_payload(base_path)
    payload.update(updates)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def active_runtime_config(config: ServerConfig) -> dict[str, Any]:
    return {
        "host": str(config.host),
        "port": int(config.port),
        "session_ttl_seconds": int(config.session_ttl_seconds),
        "run_timeout_seconds": int(config.run_timeout_seconds),
        "live_run_timeout_seconds": int(config.live_run_timeout_seconds),
        "tenant_id": str(config.tenant_id),
        "nova_shell_path": str(config.nova_shell_path or ""),
    }


def stored_runtime_config(base_path: Path, config: ServerConfig) -> dict[str, Any]:
    payload = load_server_config_payload(base_path)
    active = active_runtime_config(config)
    return {
        "host": str(payload.get("host", active["host"])),
        "port": int(payload.get("port", active["port"])),
        "session_ttl_seconds": int(payload.get("session_ttl_seconds", active["session_ttl_seconds"])),
        "run_timeout_seconds": int(payload.get("run_timeout_seconds", active["run_timeout_seconds"])),
        "live_run_timeout_seconds": int(payload.get("live_run_timeout_seconds", active["live_run_timeout_seconds"])),
        "tenant_id": str(payload.get("tenant_id", active["tenant_id"])),
        "nova_shell_path": str(payload.get("nova_shell_path", active["nova_shell_path"])),
    }


def runtime_config_requires_restart(active: dict[str, Any], stored: dict[str, Any]) -> bool:
    for key in RUNTIME_FILE_CONFIG_KEYS:
        if key == "nova_shell_path":
            if str(active.get(key, "") or "") != str(stored.get(key, "") or ""):
                return True
            continue
        if str(active.get(key)) != str(stored.get(key)):
            return True
    return False

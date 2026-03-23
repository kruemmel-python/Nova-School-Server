from __future__ import annotations

from typing import Any

from .auth import hash_password
from .database import SchoolRepository


VALID_USER_ROLES: tuple[str, ...] = ("student", "teacher", "admin")
VALID_USER_STATUSES: tuple[str, ...] = ("active", "inactive", "suspended")


class UserAdministrationService:
    def __init__(self, repository: SchoolRepository) -> None:
        self.repository = repository

    @staticmethod
    def sanitize_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
        if user is None:
            return None
        return {
            "username": user["username"],
            "display_name": user["display_name"],
            "role": user["role"],
            "permissions": dict(user.get("permissions") or {}),
            "status": user["status"],
            "created_at": user["created_at"],
            "updated_at": user["updated_at"],
        }

    def sanitize_users(self, users: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [item for item in (self.sanitize_user(user) for user in users) if item is not None]

    def update_user(
        self,
        *,
        actor_username: str,
        username: str,
        display_name: str,
        role: str,
        status: str,
        password: str = "",
    ) -> dict[str, Any]:
        current = self.repository.get_user(username)
        if current is None:
            raise FileNotFoundError("Benutzer nicht gefunden.")

        display_name = display_name.strip()
        role = role.strip()
        status = status.strip()
        password = password.strip()

        if not display_name:
            raise ValueError("Anzeigename fehlt.")
        if role not in VALID_USER_ROLES:
            raise ValueError("Ungueltige Rolle.")
        if status not in VALID_USER_STATUSES:
            raise ValueError("Ungueltiger Status.")
        if username == actor_username and role != current["role"]:
            raise ValueError("Die eigene Rolle kann in der aktuellen Sitzung nicht geaendert werden.")
        if username == actor_username and status != "active":
            raise ValueError("Das eigene Konto kann in der aktuellen Sitzung nicht deaktiviert werden.")

        updated = self.repository.update_user_account(username, display_name, role, status)
        if updated is None:
            raise FileNotFoundError("Benutzer nicht gefunden.")

        changes: dict[str, Any] = {}
        for field in ("display_name", "role", "status"):
            if current[field] != updated[field]:
                changes[field] = {"before": current[field], "after": updated[field]}

        if password:
            salt, password_hash = hash_password(password)
            self.repository.set_user_password(username, password_hash, salt)
            updated = self.repository.get_user(username) or updated
            changes["password"] = {"reset": True}

        if changes:
            self.repository.add_audit(actor_username, "admin.user.update", "user", username, {"changes": changes})

        return {
            "user": self.sanitize_user(updated),
            "changes": changes,
        }

    def permission_audit_payload(self, before: dict[str, Any] | None, after: dict[str, Any] | None) -> dict[str, Any]:
        before_permissions = dict((before or {}).get("permissions") or {})
        after_permissions = dict((after or {}).get("permissions") or {})
        changed_keys = sorted(set(before_permissions) | set(after_permissions))
        changes = {
            key: {"before": before_permissions.get(key), "after": after_permissions.get(key)}
            for key in changed_keys
            if before_permissions.get(key) != after_permissions.get(key)
        }
        return {"changes": changes}

    def audit_entries(self, username: str, limit: int = 40) -> list[dict[str, Any]]:
        return self.repository.list_audit_logs(target_type="user", target_id=username, limit=limit)

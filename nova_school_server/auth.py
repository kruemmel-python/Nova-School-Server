from __future__ import annotations

import base64
import hashlib
import hmac
import os
from dataclasses import dataclass
from typing import Any

from .database import SchoolRepository
from .permissions import resolve_permissions


@dataclass(slots=True)
class SessionContext:
    token: str
    token_id: str
    principal: Any
    user: dict[str, Any]
    groups: list[dict[str, Any]]
    permissions: dict[str, bool]

    @property
    def username(self) -> str:
        return str(self.user["username"])

    @property
    def role(self) -> str:
        return str(self.user["role"])

    @property
    def is_teacher(self) -> bool:
        return self.role in {"teacher", "admin"}

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def group_ids(self) -> list[str]:
        return [str(group["group_id"]) for group in self.groups]

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.user["username"],
            "display_name": self.user["display_name"],
            "role": self.user["role"],
            "groups": [{"group_id": group["group_id"], "display_name": group["display_name"]} for group in self.groups],
            "permissions": self.permissions,
            "token_id": self.token_id,
        }


class AuthService:
    def __init__(self, repository: SchoolRepository, security_plane: Any, tenant_id: str, session_ttl_seconds: int) -> None:
        self.repository = repository
        self.security_plane = security_plane
        self.tenant_id = tenant_id
        self.session_ttl_seconds = session_ttl_seconds
        self.security_plane.register_tenant(self.tenant_id, display_name="Nova School")

    def ensure_user(
        self,
        username: str,
        password: str,
        role: str,
        display_name: str,
        permissions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        existing = self.repository.get_user(username)
        if existing is None:
            password_salt, password_hash = hash_password(password)
            return self.repository.create_user(
                username=username,
                display_name=display_name,
                password_hash=password_hash,
                password_salt=password_salt,
                role=role,
                permissions=permissions,
            )
        return existing

    def create_user(
        self,
        username: str,
        password: str,
        role: str,
        display_name: str,
        permissions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not username.strip() or not display_name.strip() or not password:
            raise ValueError("username, display_name und password sind erforderlich")
        if role not in {"student", "teacher", "admin"}:
            raise ValueError("role muss student, teacher oder admin sein")
        if self.repository.get_user(username) is not None:
            raise ValueError(f"user already exists: {username}")
        password_salt, password_hash = hash_password(password)
        return self.repository.create_user(
            username=username,
            display_name=display_name,
            password_hash=password_hash,
            password_salt=password_salt,
            role=role,
            permissions=permissions,
        )

    def login(self, username: str, password: str) -> tuple[str, SessionContext]:
        user = self.repository.get_user(username)
        if user is None or user["status"] != "active":
            raise PermissionError("ungueltige Zugangsdaten")
        if not verify_password(password, user["password_salt"], user["password_hash"]):
            raise PermissionError("ungueltige Zugangsdaten")
        token_payload = self.security_plane.issue_token(
            self.tenant_id,
            username,
            roles={str(user["role"])},
            ttl_seconds=self.session_ttl_seconds,
            metadata={"display_name": user["display_name"], "role": user["role"]},
        )
        session = self.session_from_token(str(token_payload["token"]))
        if session is None:
            raise PermissionError("Sitzung konnte nicht erstellt werden")
        return str(token_payload["token"]), session

    def session_from_token(self, token: str) -> SessionContext | None:
        principal = self.security_plane.authenticate(token)
        if principal is None:
            return None
        user = self.repository.get_user(str(principal.subject))
        if user is None or user["status"] != "active":
            return None
        groups = self.repository.list_user_groups(user["username"])
        permissions = resolve_permissions(user["role"], [group["permissions"] for group in groups], user["permissions"])
        return SessionContext(
            token=token,
            token_id=str(principal.token_id),
            principal=principal,
            user=user,
            groups=groups,
            permissions=permissions,
        )

    def logout(self, token_id: str) -> dict[str, Any]:
        return self.security_plane.revoke_token(token_id)


def hash_password(password: str) -> tuple[str, str]:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return (
        base64.urlsafe_b64encode(salt).decode("ascii"),
        base64.urlsafe_b64encode(digest).decode("ascii"),
    )


def verify_password(password: str, salt_text: str, hash_text: str) -> bool:
    salt = base64.urlsafe_b64decode(salt_text.encode("ascii"))
    expected = base64.urlsafe_b64decode(hash_text.encode("ascii"))
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000)
    return hmac.compare_digest(actual, expected)

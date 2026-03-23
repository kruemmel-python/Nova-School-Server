from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .permissions import normalize_permission_overrides


class SchoolRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.database_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._init_schema()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _init_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    password_salt TEXT NOT NULL,
                    role TEXT NOT NULL,
                    permissions_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS groups_table (
                    group_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    permissions_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS memberships (
                    username TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    joined_at REAL NOT NULL,
                    PRIMARY KEY (username, group_id)
                );

                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    owner_type TEXT NOT NULL,
                    owner_key TEXT NOT NULL,
                    name TEXT NOT NULL,
                    slug TEXT NOT NULL,
                    template TEXT NOT NULL,
                    runtime TEXT NOT NULL,
                    main_file TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_projects_owner_slug
                ON projects(owner_type, owner_key, slug);

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    message_id TEXT PRIMARY KEY,
                    room_key TEXT NOT NULL,
                    author_username TEXT NOT NULL,
                    author_display_name TEXT NOT NULL,
                    message TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_chat_room_created
                ON chat_messages(room_key, created_at);

                CREATE TABLE IF NOT EXISTS chat_mutes (
                    mute_id TEXT PRIMARY KEY,
                    room_key TEXT NOT NULL,
                    target_username TEXT NOT NULL,
                    muted_until REAL NOT NULL,
                    reason TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_chat_mutes_target
                ON chat_mutes(room_key, target_username, muted_until);

                CREATE TABLE IF NOT EXISTS audit_logs (
                    audit_id TEXT PRIMARY KEY,
                    actor_username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target_type TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS worker_nodes (
                    worker_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    token_secret_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    endpoint_url TEXT NOT NULL,
                    advertise_host TEXT NOT NULL,
                    capabilities_json TEXT NOT NULL,
                    labels_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    last_seen_at REAL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS dispatch_jobs (
                    job_id TEXT PRIMARY KEY,
                    worker_id TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    runtime TEXT NOT NULL,
                    backend TEXT NOT NULL,
                    status TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    log_tail TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    claimed_at REAL,
                    started_at REAL,
                    finished_at REAL,
                    stop_requested INTEGER NOT NULL DEFAULT 0
                );

                CREATE INDEX IF NOT EXISTS idx_worker_nodes_status
                ON worker_nodes(status, last_seen_at);

                CREATE INDEX IF NOT EXISTS idx_dispatch_jobs_worker_status
                ON dispatch_jobs(worker_id, status, created_at);

                CREATE INDEX IF NOT EXISTS idx_dispatch_jobs_project_service
                ON dispatch_jobs(project_id, service_name, created_at);

                CREATE TABLE IF NOT EXISTS worker_request_nonces (
                    worker_id TEXT NOT NULL,
                    nonce TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY(worker_id, nonce)
                );

                CREATE INDEX IF NOT EXISTS idx_worker_request_nonces_created
                ON worker_request_nonces(created_at);
                """
            )

    @staticmethod
    def _encode_json(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @staticmethod
    def _decode_json(value: str) -> Any:
        return json.loads(value) if value else {}

    def create_user(
        self,
        username: str,
        display_name: str,
        password_hash: str,
        password_salt: str,
        role: str,
        permissions: dict[str, Any] | None = None,
        status: str = "active",
    ) -> dict[str, Any]:
        now = time.time()
        normalized_permissions = normalize_permission_overrides(permissions)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO users(username, display_name, password_hash, password_salt, role, permissions_json, status, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    display_name=excluded.display_name,
                    role=excluded.role,
                    permissions_json=excluded.permissions_json,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (
                    username,
                    display_name,
                    password_hash,
                    password_salt,
                    role,
                    self._encode_json(normalized_permissions),
                    status,
                    now,
                    now,
                ),
            )
        return self.get_user(username) or {}

    def set_user_password(self, username: str, password_hash: str, password_salt: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE users SET password_hash=?, password_salt=?, updated_at=? WHERE username=?",
                (password_hash, password_salt, time.time(), username),
            )

    def get_user(self, username: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        return self._row_to_user(row)

    def list_users(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM users ORDER BY role DESC, username ASC").fetchall()
        return [self._row_to_user(row) for row in rows if row is not None]

    def update_user_permissions(self, username: str, permissions: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE users SET permissions_json=?, updated_at=? WHERE username=?",
                (self._encode_json(normalize_permission_overrides(permissions)), time.time(), username),
            )
        return self.get_user(username)

    def update_user_account(self, username: str, display_name: str, role: str, status: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE users SET display_name=?, role=?, status=?, updated_at=? WHERE username=?",
                (display_name, role, status, time.time(), username),
            )
        return self.get_user(username)

    def set_user_status(self, username: str, status: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE users SET status=?, updated_at=? WHERE username=?", (status, time.time(), username))
        return self.get_user(username)

    def create_group(
        self,
        group_id: str,
        display_name: str,
        description: str = "",
        permissions: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = time.time()
        normalized_permissions = normalize_permission_overrides(permissions)
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO groups_table(group_id, display_name, description, permissions_json, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(group_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    description=excluded.description,
                    permissions_json=excluded.permissions_json,
                    updated_at=excluded.updated_at
                """,
                (
                    group_id,
                    display_name,
                    description,
                    self._encode_json(normalized_permissions),
                    now,
                    now,
                ),
            )
        return self.get_group(group_id) or {}

    def get_group(self, group_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM groups_table WHERE group_id=?", (group_id,)).fetchone()
        return self._row_to_group(row)

    def list_groups(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM groups_table ORDER BY display_name ASC").fetchall()
        return [self._row_to_group(row) for row in rows if row is not None]

    def update_group_permissions(self, group_id: str, permissions: dict[str, Any]) -> dict[str, Any] | None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE groups_table SET permissions_json=?, updated_at=? WHERE group_id=?",
                (self._encode_json(normalize_permission_overrides(permissions)), time.time(), group_id),
            )
        return self.get_group(group_id)

    def add_membership(self, username: str, group_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR IGNORE INTO memberships(username, group_id, joined_at) VALUES(?, ?, ?)",
                (username, group_id, time.time()),
            )

    def remove_membership(self, username: str, group_id: str) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM memberships WHERE username=? AND group_id=?", (username, group_id))

    def list_memberships(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT memberships.username, memberships.group_id, memberships.joined_at, groups_table.display_name
                FROM memberships
                LEFT JOIN groups_table ON groups_table.group_id = memberships.group_id
                ORDER BY memberships.group_id, memberships.username
                """
            ).fetchall()
        return [
            {
                "username": row["username"],
                "group_id": row["group_id"],
                "group_name": row["display_name"] or row["group_id"],
                "joined_at": row["joined_at"],
            }
            for row in rows
        ]

    def list_user_groups(self, username: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT groups_table.*
                FROM groups_table
                INNER JOIN memberships ON memberships.group_id = groups_table.group_id
                WHERE memberships.username=?
                ORDER BY groups_table.display_name
                """,
                (username,),
            ).fetchall()
        return [self._row_to_group(row) for row in rows if row is not None]

    def create_project(
        self,
        owner_type: str,
        owner_key: str,
        name: str,
        slug: str,
        template: str,
        runtime: str,
        main_file: str,
        description: str,
        created_by: str,
    ) -> dict[str, Any]:
        now = time.time()
        project_id = uuid.uuid4().hex[:12]
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO projects(project_id, owner_type, owner_key, name, slug, template, runtime, main_file, description, created_by, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (project_id, owner_type, owner_key, name, slug, template, runtime, main_file, description, created_by, now, now),
            )
        return self.get_project(project_id) or {}

    def find_project_by_owner_and_slug(self, owner_type: str, owner_key: str, slug: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM projects WHERE owner_type=? AND owner_key=? AND slug=?",
                (owner_type, owner_key, slug),
            ).fetchone()
        return self._row_to_project(row)

    def get_project(self, project_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM projects WHERE project_id=?", (project_id,)).fetchone()
        return self._row_to_project(row)

    def list_projects(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM projects ORDER BY updated_at DESC, name ASC").fetchall()
        return [self._row_to_project(row) for row in rows if row is not None]

    def list_accessible_projects(self, username: str, role: str, group_ids: list[str]) -> list[dict[str, Any]]:
        if role in {"teacher", "admin"}:
            return self.list_projects()
        placeholders = ",".join("?" for _ in group_ids) if group_ids else ""
        params: list[Any] = [username]
        query = "SELECT * FROM projects WHERE (owner_type='user' AND owner_key=?)"
        if group_ids:
            query += f" OR (owner_type='group' AND owner_key IN ({placeholders}))"
            params.extend(group_ids)
        query += " ORDER BY updated_at DESC, name ASC"
        with self._lock:
            rows = self._conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_project(row) for row in rows if row is not None]

    def put_setting(self, key: str, value: Any) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO settings(key, value_json, updated_at)
                VALUES(?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value_json=excluded.value_json,
                    updated_at=excluded.updated_at
                """,
                (key, self._encode_json(value), time.time()),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self._lock:
            row = self._conn.execute("SELECT value_json FROM settings WHERE key=?", (key,)).fetchone()
        if row is None:
            return default
        return self._decode_json(row["value_json"])

    def list_settings(self) -> dict[str, Any]:
        with self._lock:
            rows = self._conn.execute("SELECT key, value_json FROM settings ORDER BY key").fetchall()
        return {row["key"]: self._decode_json(row["value_json"]) for row in rows}

    def upsert_worker_node(
        self,
        worker_id: str,
        display_name: str,
        token_secret_name: str,
        *,
        status: str = "provisioned",
        endpoint_url: str = "",
        advertise_host: str = "",
        capabilities: list[str] | tuple[str, ...] | set[str] | None = None,
        labels: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        last_seen_at: float | None = None,
    ) -> dict[str, Any]:
        current = self.get_worker_node(worker_id)
        now = time.time()
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO worker_nodes(
                    worker_id, display_name, token_secret_name, status, endpoint_url, advertise_host,
                    capabilities_json, labels_json, metadata_json, last_seen_at, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(worker_id) DO UPDATE SET
                    display_name=excluded.display_name,
                    token_secret_name=excluded.token_secret_name,
                    status=excluded.status,
                    endpoint_url=excluded.endpoint_url,
                    advertise_host=excluded.advertise_host,
                    capabilities_json=excluded.capabilities_json,
                    labels_json=excluded.labels_json,
                    metadata_json=excluded.metadata_json,
                    last_seen_at=excluded.last_seen_at,
                    updated_at=excluded.updated_at
                """,
                (
                    worker_id,
                    display_name or worker_id,
                    token_secret_name,
                    status,
                    endpoint_url,
                    advertise_host,
                    self._encode_json(sorted(str(item) for item in (capabilities or []))),
                    self._encode_json(labels or {}),
                    self._encode_json(metadata or {}),
                    last_seen_at,
                    float(current["created_at"]) if current is not None else now,
                    now,
                ),
            )
        return self.get_worker_node(worker_id) or {}

    def get_worker_node(self, worker_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM worker_nodes WHERE worker_id=?", (worker_id,)).fetchone()
        return self._row_to_worker_node(row)

    def list_worker_nodes(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM worker_nodes ORDER BY display_name ASC, worker_id ASC").fetchall()
        return [self._row_to_worker_node(row) for row in rows if row is not None]

    def create_dispatch_job(
        self,
        *,
        worker_id: str,
        job_type: str,
        project_id: str,
        service_name: str,
        runtime: str,
        backend: str,
        payload: dict[str, Any],
        created_by: str,
    ) -> dict[str, Any]:
        now = time.time()
        job_id = uuid.uuid4().hex[:14]
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO dispatch_jobs(
                    job_id, worker_id, job_type, project_id, service_name, runtime, backend, status,
                    payload_json, result_json, log_tail, created_by, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    worker_id,
                    job_type,
                    project_id,
                    service_name,
                    runtime,
                    backend,
                    "queued",
                    self._encode_json(payload),
                    self._encode_json({}),
                    "",
                    created_by,
                    now,
                    now,
                ),
            )
        return self.get_dispatch_job(job_id) or {}

    def get_dispatch_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM dispatch_jobs WHERE job_id=?", (job_id,)).fetchone()
        return self._row_to_dispatch_job(row)

    def list_dispatch_jobs(
        self,
        *,
        project_id: str | None = None,
        worker_id: str | None = None,
        statuses: list[str] | tuple[str, ...] | set[str] | None = None,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM dispatch_jobs"
        conditions: list[str] = []
        params: list[Any] = []
        if project_id:
            conditions.append("project_id=?")
            params.append(project_id)
        if worker_id:
            conditions.append("worker_id=?")
            params.append(worker_id)
        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            conditions.append(f"status IN ({placeholders})")
            params.extend(list(statuses))
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC"
        with self._lock:
            rows = self._conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_dispatch_job(row) for row in rows if row is not None]

    def list_latest_dispatch_jobs_for_project(self, project_id: str) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT jobs.*
                FROM dispatch_jobs AS jobs
                INNER JOIN (
                    SELECT service_name, MAX(created_at) AS latest_created_at
                    FROM dispatch_jobs
                    WHERE project_id=?
                    GROUP BY service_name
                ) AS latest
                    ON latest.service_name = jobs.service_name
                   AND latest.latest_created_at = jobs.created_at
                WHERE jobs.project_id=?
                ORDER BY jobs.service_name ASC
                """,
                (project_id, project_id),
            ).fetchall()
        return [self._row_to_dispatch_job(row) for row in rows if row is not None]

    def claim_next_dispatch_job(self, worker_id: str) -> dict[str, Any] | None:
        with self._lock, self._conn:
            row = self._conn.execute(
                """
                SELECT * FROM dispatch_jobs
                WHERE worker_id=? AND status='queued'
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (worker_id,),
            ).fetchone()
            if row is None:
                return None
            now = time.time()
            self._conn.execute(
                "UPDATE dispatch_jobs SET status='claimed', claimed_at=?, updated_at=? WHERE job_id=?",
                (now, now, row["job_id"]),
            )
        return self.get_dispatch_job(str(row["job_id"]))

    def update_dispatch_job_status(
        self,
        job_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        log_tail: str | None = None,
        mark_started: bool = False,
        mark_finished: bool = False,
        clear_stop_request: bool = False,
    ) -> dict[str, Any] | None:
        current = self.get_dispatch_job(job_id)
        if current is None:
            return None
        now = time.time()
        next_result = dict(current.get("result") or {})
        if result:
            next_result.update(result)
        next_log_tail = str(log_tail if log_tail is not None else current.get("log_tail") or "")
        started_at = current.get("started_at")
        finished_at = current.get("finished_at")
        if mark_started and started_at is None:
            started_at = now
        if mark_finished:
            finished_at = now
        stop_requested = 0 if clear_stop_request else (1 if current.get("stop_requested") else 0)
        with self._lock, self._conn:
            self._conn.execute(
                """
                UPDATE dispatch_jobs
                SET status=?, result_json=?, log_tail=?, updated_at=?, started_at=?, finished_at=?, stop_requested=?
                WHERE job_id=?
                """,
                (
                    status,
                    self._encode_json(next_result),
                    next_log_tail,
                    now,
                    started_at,
                    finished_at,
                    stop_requested,
                    job_id,
                ),
            )
        return self.get_dispatch_job(job_id)

    def append_dispatch_job_log(self, job_id: str, chunk: str, *, max_chars: int = 16000) -> dict[str, Any] | None:
        current = self.get_dispatch_job(job_id)
        if current is None:
            return None
        next_log = (str(current.get("log_tail") or "") + str(chunk or ""))[-max_chars:]
        return self.update_dispatch_job_status(job_id, status=str(current.get("status") or "running"), log_tail=next_log)

    def request_dispatch_job_stop(self, job_id: str) -> dict[str, Any] | None:
        current = self.get_dispatch_job(job_id)
        if current is None:
            return None
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE dispatch_jobs SET stop_requested=1, updated_at=? WHERE job_id=?",
                (time.time(), job_id),
            )
        return self.get_dispatch_job(job_id)

    def register_worker_nonce(self, worker_id: str, nonce: str, *, ttl_seconds: int = 180) -> bool:
        now = time.time()
        cutoff = now - max(30, int(ttl_seconds))
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM worker_request_nonces WHERE created_at<?", (cutoff,))
            try:
                self._conn.execute(
                    "INSERT INTO worker_request_nonces(worker_id, nonce, created_at) VALUES(?, ?, ?)",
                    (worker_id, nonce, now),
                )
            except sqlite3.IntegrityError:
                return False
        return True

    def add_chat_message(
        self,
        room_key: str,
        author_username: str,
        author_display_name: str,
        message: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        created_at = time.time()
        message_id = uuid.uuid4().hex[:14]
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO chat_messages(message_id, room_key, author_username, author_display_name, message, metadata_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    room_key,
                    author_username,
                    author_display_name,
                    message,
                    self._encode_json(metadata or {}),
                    created_at,
                ),
            )
        return {
            "message_id": message_id,
            "room_key": room_key,
            "author_username": author_username,
            "author_display_name": author_display_name,
            "message": message,
            "metadata": metadata or {},
            "created_at": created_at,
        }

    def list_chat_messages(self, room_key: str, since: float | None = None, limit: int = 100) -> list[dict[str, Any]]:
        query = "SELECT * FROM chat_messages WHERE room_key=?"
        params: list[Any] = [room_key]
        if since is not None:
            query += " AND created_at>?"
            params.append(since)
        query += " ORDER BY created_at ASC LIMIT ?"
        params.append(max(1, min(limit, 200)))
        with self._lock:
            rows = self._conn.execute(query, tuple(params)).fetchall()
        return [
            {
                "message_id": row["message_id"],
                "room_key": row["room_key"],
                "author_username": row["author_username"],
                "author_display_name": row["author_display_name"],
                "message": row["message"],
                "metadata": self._decode_json(row["metadata_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def set_mute(self, room_key: str, target_username: str, duration_minutes: int, reason: str, created_by: str) -> dict[str, Any]:
        created_at = time.time()
        muted_until = created_at + max(1, duration_minutes) * 60
        mute_id = uuid.uuid4().hex[:12]
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO chat_mutes(mute_id, room_key, target_username, muted_until, reason, created_by, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (mute_id, room_key, target_username, muted_until, reason, created_by, created_at),
            )
        return {
            "mute_id": mute_id,
            "room_key": room_key,
            "target_username": target_username,
            "muted_until": muted_until,
            "reason": reason,
            "created_by": created_by,
            "created_at": created_at,
        }

    def get_active_mute(self, room_key: str, target_username: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._conn.execute(
                """
                SELECT * FROM chat_mutes
                WHERE target_username=?
                  AND muted_until>?
                  AND (room_key=? OR room_key='*')
                ORDER BY muted_until DESC
                LIMIT 1
                """,
                (target_username, time.time(), room_key),
            ).fetchone()
        if row is None:
            return None
        return {
            "mute_id": row["mute_id"],
            "room_key": row["room_key"],
            "target_username": row["target_username"],
            "muted_until": row["muted_until"],
            "reason": row["reason"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
        }

    def list_mutes(self, active_only: bool = False) -> list[dict[str, Any]]:
        query = "SELECT * FROM chat_mutes"
        params: tuple[Any, ...] = ()
        if active_only:
            query += " WHERE muted_until>?"
            params = (time.time(),)
        query += " ORDER BY muted_until DESC"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return [
            {
                "mute_id": row["mute_id"],
                "room_key": row["room_key"],
                "target_username": row["target_username"],
                "muted_until": row["muted_until"],
                "reason": row["reason"],
                "created_by": row["created_by"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def add_audit(self, actor_username: str, action: str, target_type: str, target_id: str, payload: dict[str, Any] | None = None) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                """
                INSERT INTO audit_logs(audit_id, actor_username, action, target_type, target_id, payload_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid.uuid4().hex[:16],
                    actor_username,
                    action,
                    target_type,
                    target_id,
                    self._encode_json(payload or {}),
                    time.time(),
                ),
            )

    def list_audit_logs(
        self,
        *,
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM audit_logs"
        clauses: list[str] = []
        params: list[Any] = []
        if target_type is not None:
            clauses.append("target_type=?")
            params.append(target_type)
        if target_id is not None:
            clauses.append("target_id=?")
            params.append(target_id)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(max(1, int(limit)))
        with self._lock:
            rows = self._conn.execute(query, tuple(params)).fetchall()
        return [
            {
                "audit_id": row["audit_id"],
                "actor_username": row["actor_username"],
                "action": row["action"],
                "target_type": row["target_type"],
                "target_id": row["target_id"],
                "payload": self._decode_json(row["payload_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _row_to_user(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "username": row["username"],
            "display_name": row["display_name"],
            "password_hash": row["password_hash"],
            "password_salt": row["password_salt"],
            "role": row["role"],
            "permissions": json.loads(row["permissions_json"]),
            "status": row["status"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _row_to_group(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "group_id": row["group_id"],
            "display_name": row["display_name"],
            "description": row["description"],
            "permissions": json.loads(row["permissions_json"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _row_to_project(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "project_id": row["project_id"],
            "owner_type": row["owner_type"],
            "owner_key": row["owner_key"],
            "name": row["name"],
            "slug": row["slug"],
            "template": row["template"],
            "runtime": row["runtime"],
            "main_file": row["main_file"],
            "description": row["description"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _row_to_worker_node(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "worker_id": row["worker_id"],
            "display_name": row["display_name"],
            "token_secret_name": row["token_secret_name"],
            "status": row["status"],
            "endpoint_url": row["endpoint_url"],
            "advertise_host": row["advertise_host"],
            "capabilities": json.loads(row["capabilities_json"]),
            "labels": json.loads(row["labels_json"]),
            "metadata": json.loads(row["metadata_json"]),
            "last_seen_at": row["last_seen_at"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    @staticmethod
    def _row_to_dispatch_job(row: sqlite3.Row | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "job_id": row["job_id"],
            "worker_id": row["worker_id"],
            "job_type": row["job_type"],
            "project_id": row["project_id"],
            "service_name": row["service_name"],
            "runtime": row["runtime"],
            "backend": row["backend"],
            "status": row["status"],
            "payload": json.loads(row["payload_json"]),
            "result": json.loads(row["result_json"]),
            "log_tail": row["log_tail"],
            "created_by": row["created_by"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "claimed_at": row["claimed_at"],
            "started_at": row["started_at"],
            "finished_at": row["finished_at"],
            "stop_requested": bool(row["stop_requested"]),
        }

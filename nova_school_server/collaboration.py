from __future__ import annotations

import json
import time
import uuid
from typing import Any

from .database import SchoolRepository
from .workspace import WorkspaceManager


class NotebookCollaborationService:
    PRESENCE_TTL_SECONDS = 25

    def __init__(self, repository: SchoolRepository, workspace_manager: WorkspaceManager) -> None:
        self.repository = repository
        self.workspace_manager = workspace_manager
        self._init_schema()

    def snapshot(self, project: dict[str, Any]) -> dict[str, Any]:
        state = self._ensure_state(project)
        return {
            "revision": state["revision"],
            "cells": state["cells"],
            "presence": self._active_presence(str(project["project_id"])),
        }

    def heartbeat(self, session: Any, project: dict[str, Any], cursor: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        project_id = str(project["project_id"])
        now = time.time()
        payload = json.dumps(cursor or {}, ensure_ascii=False)
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                """
                INSERT INTO notebook_presence(project_id, username, display_name, role, cursor_json, last_seen_at)
                VALUES(?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id, username) DO UPDATE SET
                    display_name=excluded.display_name,
                    role=excluded.role,
                    cursor_json=excluded.cursor_json,
                    last_seen_at=excluded.last_seen_at
                """,
                (project_id, session.username, session.user["display_name"], session.role, payload, now),
            )
            self.repository._conn.execute(
                "DELETE FROM notebook_presence WHERE project_id=? AND last_seen_at<?",
                (project_id, now - self.PRESENCE_TTL_SECONDS),
            )
        return self._active_presence(project_id)

    def sync(self, session: Any, project: dict[str, Any], cells: list[dict[str, Any]], base_revision: int, cursor: dict[str, Any] | None = None) -> dict[str, Any]:
        project_id = str(project["project_id"])
        current = self._ensure_state(project)
        base = self._snapshot_at(project_id, base_revision) or current
        normalized = [self._normalize_cell(cell, index) for index, cell in enumerate(cells)]
        merged = self._merge_cells(base["cells"], current["cells"], normalized)

        if merged != current["cells"]:
            revision = current["revision"] + 1
            self._store_state(project, revision, merged, session.username, base_revision)
            current = {"revision": revision, "cells": merged}
        self.workspace_manager.save_notebook(project, current["cells"])
        presence = self.heartbeat(session, project, cursor)
        return {"revision": current["revision"], "cells": current["cells"], "presence": presence}

    def _init_schema(self) -> None:
        with self.repository._lock, self.repository._conn:
            self.repository._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS notebook_collab_state (
                    project_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    updated_by TEXT NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS notebook_collab_snapshots (
                    project_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    PRIMARY KEY(project_id, revision)
                );

                CREATE TABLE IF NOT EXISTS notebook_collab_ops (
                    op_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    author_username TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS notebook_presence (
                    project_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    cursor_json TEXT NOT NULL,
                    last_seen_at REAL NOT NULL,
                    PRIMARY KEY(project_id, username)
                );
                """
            )

    def _ensure_state(self, project: dict[str, Any]) -> dict[str, Any]:
        project_id = str(project["project_id"])
        with self.repository._lock:
            row = self.repository._conn.execute(
                "SELECT revision, state_json FROM notebook_collab_state WHERE project_id=?",
                (project_id,),
            ).fetchone()
        if row is not None:
            return {"revision": int(row["revision"]), "cells": list(json.loads(row["state_json"]))}

        cells = self.workspace_manager.load_notebook(project)
        self._store_state(project, 0, cells, "system", -1)
        return {"revision": 0, "cells": cells}

    def _store_state(self, project: dict[str, Any], revision: int, cells: list[dict[str, Any]], updated_by: str, base_revision: int) -> None:
        project_id = str(project["project_id"])
        now = time.time()
        state_json = json.dumps(cells, ensure_ascii=False)
        summary = {
            "cell_ids": [str(cell.get("id") or "") for cell in cells],
            "cell_count": len(cells),
            "base_revision": base_revision,
        }
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                """
                INSERT INTO notebook_collab_state(project_id, revision, state_json, updated_by, updated_at)
                VALUES(?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    revision=excluded.revision,
                    state_json=excluded.state_json,
                    updated_by=excluded.updated_by,
                    updated_at=excluded.updated_at
                """,
                (project_id, revision, state_json, updated_by, now),
            )
            self.repository._conn.execute(
                """
                INSERT INTO notebook_collab_snapshots(project_id, revision, state_json, created_at)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(project_id, revision) DO NOTHING
                """,
                (project_id, revision, state_json, now),
            )
            self.repository._conn.execute(
                """
                INSERT INTO notebook_collab_ops(op_id, project_id, revision, author_username, summary_json, created_at)
                VALUES(?, ?, ?, ?, ?, ?)
                """,
                (uuid.uuid4().hex[:16], project_id, revision, updated_by, json.dumps(summary, ensure_ascii=False), now),
            )

    def _snapshot_at(self, project_id: str, revision: int) -> dict[str, Any] | None:
        with self.repository._lock:
            row = self.repository._conn.execute(
                "SELECT revision, state_json FROM notebook_collab_snapshots WHERE project_id=? AND revision=?",
                (project_id, revision),
            ).fetchone()
        if row is None:
            return None
        return {"revision": int(row["revision"]), "cells": list(json.loads(row["state_json"]))}

    def _active_presence(self, project_id: str) -> list[dict[str, Any]]:
        threshold = time.time() - self.PRESENCE_TTL_SECONDS
        with self.repository._lock:
            rows = self.repository._conn.execute(
                """
                SELECT username, display_name, role, cursor_json, last_seen_at
                FROM notebook_presence
                WHERE project_id=? AND last_seen_at>=?
                ORDER BY last_seen_at DESC, display_name ASC
                """,
                (project_id, threshold),
            ).fetchall()
        return [
            {
                "username": row["username"],
                "display_name": row["display_name"],
                "role": row["role"],
                "cursor": json.loads(row["cursor_json"] or "{}"),
                "last_seen_at": row["last_seen_at"],
            }
            for row in rows
        ]

    @staticmethod
    def _normalize_cell(cell: dict[str, Any], index: int) -> dict[str, Any]:
        return {
            "id": str(cell.get("id") or f"cell-{index}-{uuid.uuid4().hex[:6]}"),
            "title": str(cell.get("title") or f"Zelle {index + 1}"),
            "language": str(cell.get("language") or "python"),
            "code": str(cell.get("code") or ""),
            "stdin": str(cell.get("stdin") or ""),
            "output": str(cell.get("output") or ""),
        }

    @classmethod
    def _merge_cells(
        cls,
        base_cells: list[dict[str, Any]],
        current_cells: list[dict[str, Any]],
        incoming_cells: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        base_map = {str(cell["id"]): cls._normalize_cell(cell, index) for index, cell in enumerate(base_cells)}
        current_map = {str(cell["id"]): cls._normalize_cell(cell, index) for index, cell in enumerate(current_cells)}
        incoming_map = {str(cell["id"]): cls._normalize_cell(cell, index) for index, cell in enumerate(incoming_cells)}

        changed_ids = {
            cell_id
            for cell_id in set(base_map) | set(incoming_map)
            if incoming_map.get(cell_id) != base_map.get(cell_id)
        }
        deleted_ids = {cell_id for cell_id in base_map if cell_id not in incoming_map}

        merged_map = dict(current_map)
        for cell_id in changed_ids:
            if cell_id in incoming_map:
                merged_map[cell_id] = incoming_map[cell_id]
        for cell_id in deleted_ids:
            merged_map.pop(cell_id, None)

        ordered_ids: list[str] = []
        for cell in incoming_cells:
            cell_id = str(cell["id"])
            if cell_id in merged_map and cell_id not in ordered_ids:
                ordered_ids.append(cell_id)
        for cell in current_cells:
            cell_id = str(cell["id"])
            if cell_id in merged_map and cell_id not in ordered_ids:
                ordered_ids.append(cell_id)
        for cell_id in merged_map:
            if cell_id not in ordered_ids:
                ordered_ids.append(cell_id)
        return [merged_map[cell_id] for cell_id in ordered_ids]

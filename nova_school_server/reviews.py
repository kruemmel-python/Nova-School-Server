from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from .database import SchoolRepository
from .project_files import copy_project_snapshot, list_snapshot_files, read_text_preview
from .workspace import WorkspaceManager


class ReviewService:
    def __init__(self, repository: SchoolRepository, security_plane: Any, workspace_manager: WorkspaceManager, tenant_id: str, review_root: Path) -> None:
        self.repository = repository
        self.security_plane = security_plane
        self.workspace_manager = workspace_manager
        self.tenant_id = tenant_id
        self.review_root = review_root
        self.review_root.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def dashboard(self, session: Any) -> dict[str, Any]:
        submissions = self._list_submissions_for(session)
        assignments = self._list_assignments_for(session)
        analytics = self._analytics() if session.is_teacher else []
        return {"submissions": submissions, "assignments": assignments, "analytics": analytics}

    def submit(self, session: Any, project: dict[str, Any]) -> dict[str, Any]:
        submission_id = uuid.uuid4().hex[:12]
        snapshot_root = self.review_root / submission_id / "snapshot"
        project_root = self.workspace_manager.project_root(project)
        copied_files = copy_project_snapshot(project_root, snapshot_root)
        reviewers = self._select_reviewers(session, project)
        if not reviewers:
            raise ValueError("Keine Reviewer verfuegbar. Lege weitere Nutzer in der Gruppe an oder nutze eine Lehrkraft.")

        group_scope = [project["owner_key"]] if project["owner_type"] == "group" else session.group_ids
        now = time.time()
        metadata = {"main_file": project.get("main_file", ""), "copied_files": copied_files}
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                """
                INSERT INTO review_submissions(
                    submission_id, project_id, project_name, owner_type, owner_key, submitter_username, group_scope_json,
                    snapshot_path, review_status, assigned_count, metadata_json, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    submission_id,
                    project["project_id"],
                    project["name"],
                    project["owner_type"],
                    project["owner_key"],
                    session.username,
                    json.dumps(group_scope, ensure_ascii=False),
                    str(snapshot_root),
                    "pending",
                    len(reviewers),
                    json.dumps(metadata, ensure_ascii=False),
                    now,
                    now,
                ),
            )
            for reviewer in reviewers:
                assignment_id = uuid.uuid4().hex[:12]
                self.repository._conn.execute(
                    """
                    INSERT INTO review_assignments(
                        assignment_id, submission_id, reviewer_username, reviewer_alias, submission_alias,
                        status, feedback_json, assigned_at, completed_at, updated_at
                    )
                    VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        assignment_id,
                        submission_id,
                        reviewer["username"],
                        self._alias("Reviewer", f"{submission_id}:{reviewer['username']}"),
                        self._alias("Einreichung", f"{submission_id}:{project['project_id']}"),
                        "assigned",
                        json.dumps({}, ensure_ascii=False),
                        now,
                        None,
                        now,
                    ),
                )
        return self._submission_payload(submission_id, include_feedback=True)

    def submit_feedback(self, session: Any, assignment_id: str, feedback: dict[str, Any]) -> dict[str, Any]:
        assignment = self._assignment_row(assignment_id)
        if assignment is None:
            raise FileNotFoundError("Review-Zuweisung nicht gefunden.")
        if assignment["reviewer_username"] != session.username and not session.is_teacher:
            raise PermissionError("Nur zugewiesene Reviewer oder Lehrkraefte duerfen Feedback speichern.")
        now = time.time()
        normalized_feedback = {
            "summary": str(feedback.get("summary") or "").strip(),
            "strengths": str(feedback.get("strengths") or "").strip(),
            "risks": str(feedback.get("risks") or "").strip(),
            "questions": str(feedback.get("questions") or "").strip(),
            "score": max(1, min(5, int(feedback.get("score") or 3))),
        }
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                """
                UPDATE review_assignments
                SET status='completed', feedback_json=?, completed_at=?, updated_at=?
                WHERE assignment_id=?
                """,
                (json.dumps(normalized_feedback, ensure_ascii=False), now, now, assignment_id),
            )
        self._refresh_submission_status(str(assignment["submission_id"]))
        return self._assignment_payload(assignment_id)

    def _init_schema(self) -> None:
        with self.repository._lock, self.repository._conn:
            self.repository._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS review_submissions (
                    submission_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    owner_type TEXT NOT NULL,
                    owner_key TEXT NOT NULL,
                    submitter_username TEXT NOT NULL,
                    group_scope_json TEXT NOT NULL,
                    snapshot_path TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    assigned_count INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_assignments (
                    assignment_id TEXT PRIMARY KEY,
                    submission_id TEXT NOT NULL,
                    reviewer_username TEXT NOT NULL,
                    reviewer_alias TEXT NOT NULL,
                    submission_alias TEXT NOT NULL,
                    status TEXT NOT NULL,
                    feedback_json TEXT NOT NULL,
                    assigned_at REAL NOT NULL,
                    completed_at REAL,
                    updated_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_review_submissions_project
                ON review_submissions(project_id, created_at);

                CREATE INDEX IF NOT EXISTS idx_review_assignments_reviewer
                ON review_assignments(reviewer_username, status, assigned_at);
                """
            )

    def _select_reviewers(self, session: Any, project: dict[str, Any]) -> list[dict[str, Any]]:
        users = {user["username"]: user for user in self.repository.list_users() if user["status"] == "active"}
        memberships = self.repository.list_memberships()
        group_scope = [project["owner_key"]] if project["owner_type"] == "group" else session.group_ids
        candidate_usernames = [
            membership["username"]
            for membership in memberships
            if membership["group_id"] in group_scope and membership["username"] != session.username
        ]
        reviewers: list[dict[str, Any]] = []
        seen: set[str] = set()
        for username in sorted(candidate_usernames):
            user = users.get(username)
            if user is None or user["role"] not in {"student", "teacher", "admin"}:
                continue
            reviewers.append(user)
            seen.add(username)
            if len(reviewers) >= 2:
                return reviewers
        for username, user in sorted(users.items()):
            if username in seen or username == session.username:
                continue
            if user["role"] in {"teacher", "admin"}:
                reviewers.append(user)
                if len(reviewers) >= 2:
                    break
        return reviewers

    def _list_submissions_for(self, session: Any) -> list[dict[str, Any]]:
        query = "SELECT submission_id FROM review_submissions WHERE submitter_username=? ORDER BY created_at DESC"
        params: tuple[Any, ...] = (session.username,)
        if session.is_teacher:
            query = "SELECT submission_id FROM review_submissions ORDER BY created_at DESC LIMIT 50"
            params = ()
        with self.repository._lock:
            rows = self.repository._conn.execute(query, params).fetchall()
        return [self._submission_payload(str(row["submission_id"]), include_feedback=True) for row in rows]

    def _list_assignments_for(self, session: Any) -> list[dict[str, Any]]:
        query = "SELECT assignment_id FROM review_assignments WHERE reviewer_username=? ORDER BY assigned_at DESC"
        params: tuple[Any, ...] = (session.username,)
        if session.is_teacher:
            query = "SELECT assignment_id FROM review_assignments ORDER BY assigned_at DESC LIMIT 50"
            params = ()
        with self.repository._lock:
            rows = self.repository._conn.execute(query, params).fetchall()
        return [self._assignment_payload(str(row["assignment_id"])) for row in rows]

    def _submission_row(self, submission_id: str) -> dict[str, Any] | None:
        with self.repository._lock:
            row = self.repository._conn.execute("SELECT * FROM review_submissions WHERE submission_id=?", (submission_id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def _assignment_row(self, assignment_id: str) -> dict[str, Any] | None:
        with self.repository._lock:
            row = self.repository._conn.execute("SELECT * FROM review_assignments WHERE assignment_id=?", (assignment_id,)).fetchone()
        if row is None:
            return None
        return dict(row)

    def _submission_payload(self, submission_id: str, *, include_feedback: bool) -> dict[str, Any]:
        submission = self._submission_row(submission_id)
        if submission is None:
            raise FileNotFoundError("Review-Einreichung nicht gefunden.")
        metadata = json.loads(submission["metadata_json"] or "{}")
        snapshot_root = Path(submission["snapshot_path"])
        preview = read_text_preview(snapshot_root, str(metadata.get("main_file") or ""))
        files = list_snapshot_files(snapshot_root)
        with self.repository._lock:
            rows = self.repository._conn.execute(
                "SELECT assignment_id, reviewer_alias, submission_alias, status, feedback_json, reviewer_username FROM review_assignments WHERE submission_id=? ORDER BY assigned_at",
                (submission_id,),
            ).fetchall()
        feedback = [
            {
                "assignment_id": row["assignment_id"],
                "reviewer_alias": row["reviewer_alias"],
                "submission_alias": row["submission_alias"],
                "status": row["status"],
                "feedback": json.loads(row["feedback_json"] or "{}"),
                "reviewer_username": row["reviewer_username"],
            }
            for row in rows
        ]
        payload = {
            "submission_id": submission_id,
            "project_id": submission["project_id"],
            "project_name": submission["project_name"],
            "submitter_username": submission["submitter_username"],
            "review_status": submission["review_status"],
            "assigned_count": int(submission["assigned_count"]),
            "created_at": submission["created_at"],
            "preview": preview,
            "files": files,
            "analytics": self._project_run_analytics(str(submission["project_id"])),
        }
        if include_feedback:
            payload["feedback"] = feedback
        return payload

    def _assignment_payload(self, assignment_id: str) -> dict[str, Any]:
        assignment = self._assignment_row(assignment_id)
        if assignment is None:
            raise FileNotFoundError("Review-Zuweisung nicht gefunden.")
        submission = self._submission_payload(str(assignment["submission_id"]), include_feedback=False)
        return {
            "assignment_id": assignment_id,
            "reviewer_alias": assignment["reviewer_alias"],
            "submission_alias": assignment["submission_alias"],
            "status": assignment["status"],
            "feedback": json.loads(assignment["feedback_json"] or "{}"),
            "submission": submission,
        }

    def _refresh_submission_status(self, submission_id: str) -> None:
        with self.repository._lock:
            rows = self.repository._conn.execute(
                "SELECT status FROM review_assignments WHERE submission_id=?",
                (submission_id,),
            ).fetchall()
        statuses = [row["status"] for row in rows]
        review_status = "completed" if statuses and all(status == "completed" for status in statuses) else "in_review"
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                "UPDATE review_submissions SET review_status=?, updated_at=? WHERE submission_id=?",
                (review_status, time.time(), submission_id),
            )

    def _analytics(self) -> list[dict[str, Any]]:
        with self.repository._lock:
            rows = self.repository._conn.execute(
                "SELECT submission_id FROM review_submissions ORDER BY created_at DESC LIMIT 20"
            ).fetchall()
        return [self._submission_payload(str(row["submission_id"]), include_feedback=True) for row in rows]

    def _project_run_analytics(self, project_id: str) -> dict[str, Any]:
        with self.repository._lock:
            rows = self.repository._conn.execute(
                """
                SELECT payload_json, created_at
                FROM audit_logs
                WHERE target_type='project' AND target_id=? AND action='project.run'
                ORDER BY created_at ASC
                """,
                (project_id,),
            ).fetchall()
        run_count = len(rows)
        success_index = None
        for index, row in enumerate(rows):
            payload = json.loads(row["payload_json"] or "{}")
            if int(payload.get("returncode", 1)) == 0:
                success_index = index
                break
        return {
            "run_count": run_count,
            "failed_runs_before_success": success_index if success_index is not None else run_count,
            "succeeded": success_index is not None,
        }

    def _alias(self, prefix: str, seed: str) -> str:
        secret = self.security_plane.resolve_secret(self.tenant_id, "review-anonymizer")
        if secret is None:
            secret_value = uuid.uuid4().hex + uuid.uuid4().hex
            self.security_plane.store_secret(self.tenant_id, "review-anonymizer", secret_value, metadata={"managed_by": "nova-school"})
            secret = self.security_plane.resolve_secret(self.tenant_id, "review-anonymizer")
        secret_value = str((secret or {}).get("secret_value") or "")
        digest = hmac.new(secret_value.encode("utf-8"), seed.encode("utf-8"), hashlib.sha256).hexdigest()[:10]
        return f"{prefix}-{digest}"

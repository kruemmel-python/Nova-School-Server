from __future__ import annotations

import copy
import html
import json
import re
import time
import uuid
from typing import Any

from .curriculum_catalog import get_course, list_courses
from .curriculum_certificate_pdf import build_curriculum_certificate_pdf


FINAL_MODULE_ID = "__final__"


class CurriculumService:
    def __init__(self, repository: Any) -> None:
        self.repository = repository
        self._ensure_schema()

    def _catalog_courses(self) -> list[dict[str, Any]]:
        courses = [copy.deepcopy(course) for course in list_courses()]
        courses.extend(self._custom_courses())
        return sorted(courses, key=lambda course: (0 if not course.get("is_custom") else 1, str(course.get("title") or "").lower()))

    def _catalog_course(self, course_id: str) -> dict[str, Any] | None:
        custom = self._custom_course(course_id)
        if custom is not None:
            return custom
        course = get_course(course_id)
        return copy.deepcopy(course) if course else None

    def _custom_courses(self) -> list[dict[str, Any]]:
        with self.repository._lock:
            rows = self.repository._conn.execute(
                "SELECT payload_json, created_by, updated_by, created_at, updated_at FROM curriculum_custom_courses ORDER BY updated_at DESC, title ASC"
            ).fetchall()
        courses: list[dict[str, Any]] = []
        for row in rows:
            payload = json.loads(row["payload_json"] or "{}")
            payload["is_custom"] = True
            payload["created_by"] = row["created_by"]
            payload["updated_by"] = row["updated_by"]
            payload["created_at"] = row["created_at"]
            payload["updated_at"] = row["updated_at"]
            courses.append(payload)
        return courses

    def _custom_course(self, course_id: str) -> dict[str, Any] | None:
        with self.repository._lock:
            row = self.repository._conn.execute(
                "SELECT payload_json, created_by, updated_by, created_at, updated_at FROM curriculum_custom_courses WHERE course_id=?",
                (course_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row["payload_json"] or "{}")
        payload["is_custom"] = True
        payload["created_by"] = row["created_by"]
        payload["updated_by"] = row["updated_by"]
        payload["created_at"] = row["created_at"]
        payload["updated_at"] = row["updated_at"]
        return payload

    @staticmethod
    def _slug(value: str) -> str:
        text = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower())
        return text.strip("-")

    @staticmethod
    def _listify(value: Any, *, separator: str = "\n") -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            if separator == ",":
                items = value.split(",")
            else:
                items = value.splitlines()
            return [item.strip() for item in items if item.strip()]
        return []

    def _normalize_question(self, raw: dict[str, Any], *, fallback_id: str) -> dict[str, Any]:
        question_id = self._slug(str(raw.get("id") or fallback_id)) or fallback_id
        question_type = str(raw.get("type") or "single").strip().lower()
        if question_type not in {"single", "multi", "text"}:
            raise ValueError("Fragentyp muss single, multi oder text sein.")
        prompt = str(raw.get("prompt") or "").strip()
        if not prompt:
            raise ValueError("Jede Frage braucht einen Prompt.")
        explanation = str(raw.get("explanation") or "").strip()
        points = max(1.0, float(raw.get("points") or 1))
        payload: dict[str, Any] = {
            "id": question_id,
            "type": question_type,
            "prompt": prompt,
            "points": points,
            "explanation": explanation,
        }
        if question_type in {"single", "multi"}:
            raw_options = raw.get("options") or []
            options: list[dict[str, str]] = []
            for index, option in enumerate(list(raw_options), start=1):
                option_id = self._slug(str((option or {}).get("id") or f"option-{index}")) or f"option-{index}"
                label = str((option or {}).get("label") or "").strip()
                if label:
                    options.append({"id": option_id, "label": label})
            if len(options) < 2:
                raise ValueError("Single- und Multi-Fragen brauchen mindestens zwei Optionen.")
            payload["options"] = options
            raw_correct = self._listify(raw.get("correct"), separator=",")
            correct = [item for item in raw_correct if item in {option["id"] for option in options}]
            if question_type == "single":
                if len(correct) != 1:
                    raise ValueError("Single-Choice-Fragen brauchen genau eine korrekte Option.")
                payload["correct"] = [correct[0]]
            else:
                if not correct:
                    raise ValueError("Multi-Choice-Fragen brauchen mindestens eine korrekte Option.")
                payload["correct"] = correct
        else:
            accepted = self._listify(raw.get("accepted"))
            if not accepted:
                raise ValueError("Textfragen brauchen mindestens eine akzeptierte Antwort.")
            payload["accepted"] = accepted
            payload["placeholder"] = str(raw.get("placeholder") or "").strip()
        return payload

    def _normalize_course_definition(self, payload: dict[str, Any], *, editor_username: str) -> dict[str, Any]:
        requested_course_id = str(payload.get("course_id") or "").strip()
        course_id = self._slug(requested_course_id)
        if not course_id:
            raise ValueError("Kurs-ID fehlt.")
        if get_course(course_id) is not None and self._custom_course(course_id) is None:
            raise ValueError("Vordefinierte Standardkurse koennen nicht direkt ueberschrieben werden.")
        title = str(payload.get("title") or "").strip()
        if not title:
            raise ValueError("Kurstitel fehlt.")
        modules_raw = list(payload.get("modules") or [])
        if not modules_raw:
            raise ValueError("Ein Kurs braucht mindestens ein Mini-Modul.")
        modules: list[dict[str, Any]] = []
        seen_module_ids: set[str] = set()
        for index, raw_module in enumerate(modules_raw, start=1):
            base_title = str((raw_module or {}).get("title") or f"Mini-Modul {index}").strip()
            module_id = self._slug(str((raw_module or {}).get("module_id") or f"m{index:02d}_{base_title}")) or f"m{index:02d}"
            if module_id in seen_module_ids:
                raise ValueError("Mini-Modul-IDs muessen eindeutig sein.")
            seen_module_ids.add(module_id)
            questions = [
                self._normalize_question(dict(question or {}), fallback_id=f"{module_id}_q{question_index}")
                for question_index, question in enumerate(list((raw_module or {}).get("questions") or []), start=1)
            ]
            if not questions:
                raise ValueError("Jedes Mini-Modul braucht mindestens eine Frage.")
            modules.append(
                {
                    "module_id": module_id,
                    "title": base_title,
                    "estimated_minutes": max(10, int((raw_module or {}).get("estimated_minutes") or 30)),
                    "objectives": self._listify((raw_module or {}).get("objectives")),
                    "lesson_markdown": str((raw_module or {}).get("lesson_markdown") or "").strip(),
                    "quiz_pass_ratio": min(1.0, max(0.1, float((raw_module or {}).get("quiz_pass_ratio") or payload.get("pass_ratio") or 0.7))),
                    "questions": questions,
                }
            )
        final_raw = dict(payload.get("final_assessment") or {})
        final_questions = [
            self._normalize_question(dict(question or {}), fallback_id=f"{course_id}_final_q{index}")
            for index, question in enumerate(list(final_raw.get("questions") or []), start=1)
        ]
        if not final_questions:
            raise ValueError("Die Abschlusspruefung braucht mindestens eine Frage.")
        theme = dict(payload.get("certificate_theme") or {})
        normalized = {
            "course_id": course_id,
            "title": title,
            "subtitle": str(payload.get("subtitle") or "").strip(),
            "subject_area": str(payload.get("subject_area") or "").strip(),
            "summary": str(payload.get("summary") or "").strip(),
            "audience": str(payload.get("audience") or "").strip(),
            "estimated_hours": max(1, int(payload.get("estimated_hours") or 1)),
            "certificate_title": str(payload.get("certificate_title") or f"Nova School Zertifikat {title}").strip(),
            "pass_ratio": min(1.0, max(0.1, float(payload.get("pass_ratio") or 0.7))),
            "final_pass_ratio": min(1.0, max(0.1, float(payload.get("final_pass_ratio") or 0.75))),
            "certificate_theme": {
                "label": str(theme.get("label") or payload.get("subject_area") or title).strip(),
                "accent": str(theme.get("accent") or "").strip(),
                "accent_dark": str(theme.get("accent_dark") or "").strip(),
                "warm": str(theme.get("warm") or "").strip(),
                "paper": str(theme.get("paper") or "").strip(),
            },
            "modules": modules,
            "final_assessment": {
                "assessment_id": str(final_raw.get("assessment_id") or f"{course_id}-abschluss").strip(),
                "title": str(final_raw.get("title") or f"Abschlusspruefung {title}").strip(),
                "instructions": str(final_raw.get("instructions") or "").strip(),
                "questions": final_questions,
            },
            "is_custom": True,
            "updated_by": editor_username,
        }
        return normalized

    def save_custom_course(self, session: Any, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize_course_definition(dict(payload or {}), editor_username=session.username)
        current = self._custom_course(normalized["course_id"])
        now = time.time()
        created_by = str(current.get("created_by") if current else session.username)
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                """
                INSERT INTO curriculum_custom_courses(course_id, title, payload_json, created_by, updated_by, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(course_id) DO UPDATE SET
                    title=excluded.title,
                    payload_json=excluded.payload_json,
                    updated_by=excluded.updated_by,
                    updated_at=excluded.updated_at
                """,
                (
                    normalized["course_id"],
                    normalized["title"],
                    json.dumps(normalized, ensure_ascii=False),
                    created_by,
                    session.username,
                    float(current.get("created_at") if current else now),
                    now,
                ),
            )
        return self._custom_course(normalized["course_id"]) or normalized

    def dashboard(self, session: Any) -> dict[str, Any]:
        courses = [self._course_payload(session, course) for course in self._catalog_courses()]
        payload: dict[str, Any] = {"courses": courses}
        if session.permissions.get("curriculum.manage", False) or getattr(session, "is_teacher", False):
            payload["manager"] = {
                "users": [self._sanitize_user(user) for user in self.repository.list_users()],
                "groups": self.repository.list_groups(),
                "releases": self._list_releases(),
                "learners": self._learner_overview(),
                "course_definitions": [copy.deepcopy(course) for course in self._catalog_courses()],
            }
        return payload

    def attempt_history(self, course_id: str, username: str) -> dict[str, Any]:
        course = self._catalog_course(course_id)
        if course is None:
            raise FileNotFoundError("Kurs nicht gefunden.")
        user = self.repository.get_user(username)
        if user is None:
            raise FileNotFoundError("Benutzer nicht gefunden.")
        with self.repository._lock:
            rows = self.repository._conn.execute(
                """
                SELECT * FROM curriculum_attempts
                WHERE course_id=? AND username=?
                ORDER BY submitted_at DESC
                """,
                (course_id, username),
            ).fetchall()
        module_titles = {module["module_id"]: module["title"] for module in course["modules"]}
        attempts: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            module_key = str(item["module_id"])
            attempts.append(
                {
                    "attempt_id": item["attempt_id"],
                    "course_id": item["course_id"],
                    "module_id": module_key,
                    "module_title": "Abschlusspruefung" if module_key == FINAL_MODULE_ID else module_titles.get(module_key, module_key),
                    "assessment_kind": item["assessment_kind"],
                    "username": item["username"],
                    "score": float(item["score"]),
                    "max_score": float(item["max_score"]),
                    "passed": bool(item["passed"]),
                    "submitted_at": item["submitted_at"],
                    "feedback": json.loads(item["feedback_json"] or "[]"),
                }
            )
        learner_session = type(
            "CurriculumSession",
            (),
            {
                "username": username,
                "is_teacher": False,
                "permissions": {"curriculum.use": True},
                "group_ids": [group["group_id"] for group in self.repository.list_user_groups(username)],
            },
        )()
        course_payload = self._course_payload(learner_session, course)
        return {
            "learner": self._sanitize_user(user),
            "course": {
                "course_id": course["course_id"],
                "title": course["title"],
                "subject_area": course.get("subject_area", ""),
                "subtitle": course["subtitle"],
            },
            "progress": course_payload["progress"],
            "attempts": attempts,
        }

    def set_release(self, session: Any, course_id: str, scope_type: str, scope_key: str, enabled: bool, note: str = "") -> dict[str, Any]:
        course = self._catalog_course(course_id)
        if course is None:
            raise FileNotFoundError("Kurs nicht gefunden.")
        if scope_type not in {"user", "group"}:
            raise ValueError("scope_type muss 'user' oder 'group' sein.")
        scope_key = str(scope_key or "").strip()
        if not scope_key:
            raise ValueError("scope_key fehlt.")
        now = time.time()
        release_id = f"{course_id}:{scope_type}:{scope_key}"
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                """
                INSERT INTO curriculum_releases(release_id, course_id, scope_type, scope_key, enabled, note, granted_by, created_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(release_id) DO UPDATE SET
                    enabled=excluded.enabled,
                    note=excluded.note,
                    granted_by=excluded.granted_by,
                    updated_at=excluded.updated_at
                """,
                (release_id, course_id, scope_type, scope_key, 1 if enabled else 0, note.strip(), session.username, now, now),
            )
        return self._release_payload(release_id)

    def submit_assessment(self, session: Any, course_id: str, module_id: str, assessment_kind: str, answers: dict[str, Any]) -> dict[str, Any]:
        course = self._catalog_course(course_id)
        if course is None:
            raise FileNotFoundError("Kurs nicht gefunden.")
        release = self._resolve_release(session, course_id)
        if not release["enabled"] and not getattr(session, "is_teacher", False):
            raise PermissionError("Dieser Kurs ist fuer diese Sitzung noch nicht freigeschaltet.")

        module = self._resolve_module(course, module_id, assessment_kind)
        course_payload = self._course_payload(session, course)
        if assessment_kind == "final":
            if not bool(course_payload["progress"]["final_unlocked"]) and not getattr(session, "is_teacher", False):
                raise PermissionError("Die Abschlusspruefung ist erst nach allen bestandenen Mini-Modulen freigeschaltet.")
        else:
            module_payload = next((item for item in course_payload["modules"] if item["module_id"] == module_id), None)
            if module_payload is None:
                raise FileNotFoundError("Mini-Modul nicht gefunden.")
            if module_payload["status"] == "locked" and not getattr(session, "is_teacher", False):
                raise PermissionError("Dieses Mini-Modul ist noch nicht freigeschaltet.")

        pass_ratio = course.get("final_pass_ratio", course.get("pass_ratio", 0.75)) if assessment_kind == "final" else module.get("quiz_pass_ratio", course.get("pass_ratio", 0.7))
        grading = self._grade_assessment(module, dict(answers or {}), pass_ratio)
        attempt_id = uuid.uuid4().hex[:12]
        now = time.time()
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                """
                INSERT INTO curriculum_attempts(
                    attempt_id, course_id, module_id, assessment_kind, username, answers_json,
                    score, max_score, passed, feedback_json, submitted_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    attempt_id,
                    course_id,
                    FINAL_MODULE_ID if assessment_kind == "final" else module_id,
                    assessment_kind,
                    session.username,
                    json.dumps(dict(answers or {}), ensure_ascii=False),
                    grading["score"],
                    grading["max_score"],
                    1 if grading["passed"] else 0,
                    json.dumps(grading["feedback"], ensure_ascii=False),
                    now,
                ),
            )
        certificate = self._refresh_certificate(session.username, course_id, grading if assessment_kind == "final" else None)
        return {
            "attempt_id": attempt_id,
            "course_id": course_id,
            "module_id": module_id,
            "assessment_kind": assessment_kind,
            "score": grading["score"],
            "max_score": grading["max_score"],
            "passed": grading["passed"],
            "feedback": grading["feedback"],
            "certificate": certificate,
            "course": self._course_payload(session, course),
        }

    def build_certificate_pdf(self, session: Any, course_id: str, school_name: str) -> dict[str, Any]:
        course = self._catalog_course(course_id)
        if course is None:
            raise FileNotFoundError("Kurs nicht gefunden.")
        certificate = self._certificate_for(session.username, course_id)
        if certificate is None or certificate.get("status") != "issued":
            raise FileNotFoundError("Fuer diesen Kurs liegt noch kein Zertifikat vor.")
        user = self.repository.get_user(session.username) or {}
        student_name = str(user.get("display_name") or session.username)
        pdf_bytes = build_curriculum_certificate_pdf(
            school_name=school_name,
            student_name=student_name,
            course_title=course["title"],
            certificate_title=course.get("certificate_title") or f"Zertifikat {course['title']}",
            subject_label=str(course.get("subject_area") or ""),
            theme=dict(course.get("certificate_theme") or {}),
            score=float(certificate["score"]),
            max_score=float(certificate["metadata"].get("max_score", certificate["score"])),
            issued_at=float(certificate["issued_at"]),
            certificate_id=str(certificate["certificate_id"]),
            verification_url=str(certificate["metadata"].get("verification_url", "")),
            signatory_name=str(certificate["metadata"].get("signatory_name", "")),
            signatory_title=str(certificate["metadata"].get("signatory_title", "")),
            logo_path=str(certificate["metadata"].get("logo_path", "")),
        )
        filename = f"{course_id}-{session.username}-zertifikat.pdf"
        return {"filename": filename, "content_type": "application/pdf", "content": pdf_bytes, "certificate": certificate}

    def prepare_certificate_metadata(
        self,
        username: str,
        course_id: str,
        *,
        verification_url: str,
        signatory_name: str = "",
        signatory_title: str = "",
        logo_path: str = "",
    ) -> dict[str, Any] | None:
        certificate = self._certificate_for(username, course_id)
        if certificate is None:
            return None
        metadata = dict(certificate["metadata"] or {})
        metadata["verification_url"] = str(verification_url or "").strip()
        metadata["signatory_name"] = str(signatory_name or "").strip()
        metadata["signatory_title"] = str(signatory_title or "").strip()
        metadata["logo_path"] = str(logo_path or "").strip()
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                "UPDATE curriculum_certificates SET metadata_json=?, updated_at=? WHERE certificate_id=?",
                (json.dumps(metadata, ensure_ascii=False), time.time(), certificate["certificate_id"]),
            )
        return self._certificate_for(username, course_id)

    def certificate_by_id(self, certificate_id: str) -> dict[str, Any] | None:
        with self.repository._lock:
            row = self.repository._conn.execute(
                "SELECT * FROM curriculum_certificates WHERE certificate_id=?",
                (certificate_id,),
            ).fetchone()
        if row is None:
            return None
        metadata = json.loads(row["metadata_json"] or "{}")
        user = self.repository.get_user(str(row["username"])) or {}
        course = self._catalog_course(str(row["course_id"])) or {}
        return {
            "certificate_id": row["certificate_id"],
            "course_id": row["course_id"],
            "course_title": course.get("title") or row["course_id"],
            "certificate_title": course.get("certificate_title") or f"Zertifikat {course.get('title') or row['course_id']}",
            "subject_area": course.get("subject_area") or "",
            "username": row["username"],
            "student_name": user.get("display_name") or row["username"],
            "score": row["score"],
            "status": row["status"],
            "issued_at": row["issued_at"],
            "updated_at": row["updated_at"],
            "metadata": metadata,
        }

    def render_certificate_verification_page(self, certificate_id: str, school_name: str) -> str:
        payload = self.certificate_by_id(certificate_id)
        if payload is None:
            title = "Zertifikat nicht gefunden"
            body = """
              <article class="verify-card">
                <h1>Zertifikat nicht gefunden</h1>
                <p>Der angegebene Pruefcode ist auf diesem Server nicht bekannt.</p>
              </article>
            """
        else:
            title = "Zertifikat verifiziert"
            body = f"""
              <article class="verify-card">
                <p class="eyebrow">Zertifikatspruefung</p>
                <h1>Zertifikat verifiziert</h1>
                <p>Dieses Zertifikat wurde auf dem Nova School Server der Einrichtung <strong>{html.escape(school_name)}</strong> erstellt.</p>
                <dl class="verify-grid">
                  <div><dt>Schueler</dt><dd>{html.escape(str(payload['student_name']))}</dd></div>
                  <div><dt>Kurs</dt><dd>{html.escape(str(payload['course_title']))}</dd></div>
                  <div><dt>Fachbereich</dt><dd>{html.escape(str(payload['subject_area'] or '-'))}</dd></div>
                  <div><dt>Zertifikatsnummer</dt><dd>{html.escape(str(payload['certificate_id']))}</dd></div>
                  <div><dt>Status</dt><dd>{html.escape(str(payload['status']))}</dd></div>
                  <div><dt>Punktzahl</dt><dd>{html.escape(str(payload['score']))}</dd></div>
                  <div><dt>Ausgestellt</dt><dd>{time.strftime('%d.%m.%Y %H:%M', time.localtime(float(payload['issued_at'])))}</dd></div>
                </dl>
              </article>
            """
        return f"""<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{html.escape(title)} | Nova School Server</title>
    <style>
      :root {{
        color-scheme: light;
        --bg: #f4ead7;
        --panel: rgba(255,255,252,0.94);
        --ink: #182126;
        --muted: #5e6c6e;
        --accent: #126d67;
        --warm: #8f412f;
        --line: rgba(24,33,38,0.12);
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        min-height: 100vh;
        font-family: Georgia, "Times New Roman", serif;
        color: var(--ink);
        background: linear-gradient(135deg, #f7eed9 0%, #d8e8df 52%, #bfd1d7 100%);
        padding: 2rem;
      }}
      .verify-shell {{
        max-width: 860px;
        margin: 0 auto;
      }}
      .verify-card {{
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 28px;
        padding: 2rem;
        box-shadow: 0 28px 80px rgba(24,33,38,0.14);
      }}
      .eyebrow {{
        margin: 0 0 .4rem;
        letter-spacing: .2em;
        text-transform: uppercase;
        color: var(--warm);
        font-size: .82rem;
      }}
      h1 {{ margin: 0 0 1rem; }}
      p {{ line-height: 1.6; }}
      .verify-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1rem;
        margin: 1.5rem 0 0;
      }}
      .verify-grid div {{
        background: rgba(255,255,255,0.76);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: .9rem 1rem;
      }}
      dt {{
        font-size: .85rem;
        color: var(--muted);
        margin-bottom: .25rem;
      }}
      dd {{
        margin: 0;
        font-weight: 600;
      }}
    </style>
  </head>
  <body>
    <main class="verify-shell">
      {body}
    </main>
  </body>
</html>"""

    def _ensure_schema(self) -> None:
        with self.repository._lock, self.repository._conn:
            self.repository._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS curriculum_releases (
                    release_id TEXT PRIMARY KEY,
                    course_id TEXT NOT NULL,
                    scope_type TEXT NOT NULL,
                    scope_key TEXT NOT NULL,
                    enabled INTEGER NOT NULL,
                    note TEXT NOT NULL,
                    granted_by TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_curriculum_releases_scope
                ON curriculum_releases(course_id, scope_type, scope_key);

                CREATE TABLE IF NOT EXISTS curriculum_attempts (
                    attempt_id TEXT PRIMARY KEY,
                    course_id TEXT NOT NULL,
                    module_id TEXT NOT NULL,
                    assessment_kind TEXT NOT NULL,
                    username TEXT NOT NULL,
                    answers_json TEXT NOT NULL,
                    score REAL NOT NULL,
                    max_score REAL NOT NULL,
                    passed INTEGER NOT NULL,
                    feedback_json TEXT NOT NULL,
                    submitted_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_curriculum_attempts_course_user
                ON curriculum_attempts(course_id, username, submitted_at DESC);

                CREATE TABLE IF NOT EXISTS curriculum_certificates (
                    certificate_id TEXT PRIMARY KEY,
                    course_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    score REAL NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    issued_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE UNIQUE INDEX IF NOT EXISTS idx_curriculum_certificates_course_user
                ON curriculum_certificates(course_id, username);

                CREATE TABLE IF NOT EXISTS curriculum_custom_courses (
                    course_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    updated_by TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                """
            )

    @staticmethod
    def _sanitize_user(user: dict[str, Any]) -> dict[str, Any]:
        return {
            "username": user.get("username"),
            "display_name": user.get("display_name"),
            "role": user.get("role"),
            "status": user.get("status"),
        }

    def _resolve_release(self, session: Any, course_id: str) -> dict[str, Any]:
        if getattr(session, "is_teacher", False):
            return {"enabled": True, "source": "teacher", "scope_type": "teacher", "scope_key": session.username, "note": "Lehrkraftzugriff"}

        user_rows = self._query_releases(course_id, "user", [session.username])
        if user_rows:
            row = user_rows[0]
            return {"enabled": bool(row["enabled"]), "source": "user", "scope_type": "user", "scope_key": row["scope_key"], "note": row["note"], "updated_at": row["updated_at"]}

        group_rows = self._query_releases(course_id, "group", list(getattr(session, "group_ids", []) or []))
        enabled_group = next((row for row in group_rows if bool(row["enabled"])), None)
        if enabled_group:
            return {"enabled": True, "source": "group", "scope_type": "group", "scope_key": enabled_group["scope_key"], "note": enabled_group["note"], "updated_at": enabled_group["updated_at"]}

        return {"enabled": False, "source": "none", "scope_type": "", "scope_key": "", "note": ""}

    def _query_releases(self, course_id: str, scope_type: str, scope_keys: list[str]) -> list[dict[str, Any]]:
        if not scope_keys:
            return []
        placeholders = ",".join("?" for _ in scope_keys)
        query = f"SELECT * FROM curriculum_releases WHERE course_id=? AND scope_type=? AND scope_key IN ({placeholders}) ORDER BY updated_at DESC"
        with self.repository._lock:
            rows = self.repository._conn.execute(query, (course_id, scope_type, *scope_keys)).fetchall()
        return [dict(row) for row in rows]

    def _list_releases(self) -> list[dict[str, Any]]:
        with self.repository._lock:
            rows = self.repository._conn.execute("SELECT * FROM curriculum_releases ORDER BY updated_at DESC").fetchall()
        return [self._release_row_payload(dict(row)) for row in rows]

    def _release_payload(self, release_id: str) -> dict[str, Any]:
        with self.repository._lock:
            row = self.repository._conn.execute("SELECT * FROM curriculum_releases WHERE release_id=?", (release_id,)).fetchone()
        if row is None:
            raise FileNotFoundError("Freigabe nicht gefunden.")
        return self._release_row_payload(dict(row))

    def _release_row_payload(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "release_id": row["release_id"],
            "course_id": row["course_id"],
            "scope_type": row["scope_type"],
            "scope_key": row["scope_key"],
            "enabled": bool(row["enabled"]),
            "note": row["note"],
            "granted_by": row["granted_by"],
            "updated_at": row["updated_at"],
        }

    def _latest_attempts(self, username: str, course_id: str) -> dict[tuple[str, str], dict[str, Any]]:
        with self.repository._lock:
            rows = self.repository._conn.execute(
                "SELECT * FROM curriculum_attempts WHERE course_id=? AND username=? ORDER BY submitted_at DESC",
                (course_id, username),
            ).fetchall()
        latest: dict[tuple[str, str], dict[str, Any]] = {}
        for row in rows:
            key = (row["assessment_kind"], row["module_id"])
            if key not in latest:
                latest[key] = dict(row)
        return latest

    def _certificate_for(self, username: str, course_id: str) -> dict[str, Any] | None:
        with self.repository._lock:
            row = self.repository._conn.execute(
                "SELECT * FROM curriculum_certificates WHERE course_id=? AND username=?",
                (course_id, username),
            ).fetchone()
        if row is None:
            return None
        metadata = json.loads(row["metadata_json"] or "{}")
        return {
            "certificate_id": row["certificate_id"],
            "course_id": row["course_id"],
            "username": row["username"],
            "score": row["score"],
            "status": row["status"],
            "issued_at": row["issued_at"],
            "updated_at": row["updated_at"],
            "metadata": metadata,
        }

    def _course_payload(self, session: Any, course: dict[str, Any]) -> dict[str, Any]:
        release = self._resolve_release(session, course["course_id"])
        attempts = self._latest_attempts(session.username, course["course_id"])
        certificate = self._certificate_for(session.username, course["course_id"])
        released = bool(release["enabled"])
        previous_passed = released or getattr(session, "is_teacher", False)
        passed_modules = 0
        modules: list[dict[str, Any]] = []

        for index, module in enumerate(course["modules"], start=1):
            row = attempts.get(("module", module["module_id"]))
            passed = bool(row and row["passed"])
            if passed:
                passed_modules += 1
            status = "locked"
            if getattr(session, "is_teacher", False) or released:
                status = "passed" if passed else ("available" if previous_passed else "locked")
            modules.append(
                {
                    "module_id": module["module_id"],
                    "title": module["title"],
                    "estimated_minutes": module["estimated_minutes"],
                    "objectives": list(module["objectives"]),
                    "lesson_markdown": module["lesson_markdown"],
                    "status": status,
                    "passed": passed,
                    "attempt_count": self._attempt_count(session.username, course["course_id"], module["module_id"], "module"),
                    "last_score": float(row["score"]) if row else 0.0,
                    "last_max_score": float(row["max_score"]) if row else 0.0,
                    "quiz": {
                        "assessment_id": f"{course['course_id']}:{module['module_id']}",
                        "pass_ratio": module.get("quiz_pass_ratio", course.get("pass_ratio", 0.7)),
                        "questions": list(module["questions"]),
                    },
                    "index": index,
                }
            )
            previous_passed = previous_passed and passed

        final_row = attempts.get(("final", FINAL_MODULE_ID))
        final_unlocked = released and all(item["passed"] for item in modules)
        final_passed = bool(final_row and final_row["passed"])
        return {
            "course_id": course["course_id"],
            "title": course["title"],
            "subtitle": course["subtitle"],
            "subject_area": course.get("subject_area", ""),
            "summary": course["summary"],
            "audience": course["audience"],
            "estimated_hours": course["estimated_hours"],
            "release": release,
            "modules": modules,
            "progress": {
                "passed_modules": passed_modules,
                "total_modules": len(modules),
                "percent": int((passed_modules / len(modules)) * 100) if modules else 0,
                "final_unlocked": final_unlocked or getattr(session, "is_teacher", False),
                "final_passed": final_passed,
                "certified": bool(certificate and certificate["status"] == "issued"),
            },
            "final_assessment": {
                "assessment_id": course["final_assessment"]["assessment_id"],
                "title": course["final_assessment"]["title"],
                "instructions": course["final_assessment"]["instructions"],
                "unlocked": final_unlocked or getattr(session, "is_teacher", False),
                "passed": final_passed,
                "attempt_count": self._attempt_count(session.username, course["course_id"], FINAL_MODULE_ID, "final"),
                "last_score": float(final_row["score"]) if final_row else 0.0,
                "last_max_score": float(final_row["max_score"]) if final_row else 0.0,
                "pass_ratio": course.get("final_pass_ratio", 0.75),
                "questions": list(course["final_assessment"]["questions"]),
            },
            "certificate": certificate,
        }

    def _attempt_count(self, username: str, course_id: str, module_id: str, assessment_kind: str) -> int:
        with self.repository._lock:
            row = self.repository._conn.execute(
                "SELECT COUNT(*) AS count FROM curriculum_attempts WHERE username=? AND course_id=? AND module_id=? AND assessment_kind=?",
                (username, course_id, module_id, assessment_kind),
            ).fetchone()
        return int(row["count"] if row else 0)

    @staticmethod
    def _resolve_module(course: dict[str, Any], module_id: str, assessment_kind: str) -> dict[str, Any]:
        if assessment_kind == "final":
            module = dict(course["final_assessment"])
            module["questions"] = list(course["final_assessment"]["questions"])
            return module
        for module in course["modules"]:
            if module["module_id"] == module_id:
                return dict(module)
        raise FileNotFoundError("Mini-Modul nicht gefunden.")

    @staticmethod
    def _grade_assessment(module: dict[str, Any], answers: dict[str, Any], pass_ratio: float) -> dict[str, Any]:
        feedback: list[dict[str, Any]] = []
        score = 0.0
        max_score = 0.0
        for question in module["questions"]:
            earned = 0.0
            points = float(question.get("points", 1))
            max_score += points
            answer = answers.get(question["id"])
            correct = False
            if question["type"] == "single":
                value = str(answer or "").strip()
                correct = value in set(question.get("correct", []))
            elif question["type"] == "multi":
                submitted = {str(item).strip() for item in list(answer or []) if str(item).strip()}
                correct = submitted == set(question.get("correct", []))
            elif question["type"] == "text":
                normalized = str(answer or "").strip().lower()
                correct = normalized in {item.strip().lower() for item in question.get("accepted", [])}
            if correct:
                earned = points
                score += points
            feedback.append(
                {
                    "question_id": question["id"],
                    "prompt": question["prompt"],
                    "correct": correct,
                    "earned": earned,
                    "points": points,
                    "explanation": question.get("explanation", ""),
                }
            )
        passed = bool(max_score) and (score / max_score) >= float(pass_ratio or 0.0)
        return {"score": score, "max_score": max_score, "passed": passed, "feedback": feedback}

    def _refresh_certificate(self, username: str, course_id: str, final_grading: dict[str, Any] | None) -> dict[str, Any] | None:
        course = self._catalog_course(course_id)
        if course is None:
            return None
        attempts = self._latest_attempts(username, course_id)
        modules_passed = all(bool(attempts.get(("module", module["module_id"])) and attempts.get(("module", module["module_id"]))["passed"]) for module in course["modules"])
        final_row = attempts.get(("final", FINAL_MODULE_ID))
        final_passed = bool(final_grading["passed"]) if final_grading is not None else bool(final_row and final_row["passed"])
        if not modules_passed or not final_passed:
            return self._certificate_for(username, course_id)
        score = float(final_grading["score"]) if final_grading is not None else float(final_row["score"])
        max_score = float(final_grading["max_score"]) if final_grading is not None else float(final_row["max_score"])
        payload = {"course_title": course["title"], "score": score, "max_score": max_score}
        now = time.time()
        certificate_id = f"{course_id}:{username}"
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                """
                INSERT INTO curriculum_certificates(certificate_id, course_id, username, score, status, metadata_json, issued_at, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(certificate_id) DO UPDATE SET
                    score=excluded.score,
                    status=excluded.status,
                    metadata_json=excluded.metadata_json,
                    updated_at=excluded.updated_at
                """,
                (certificate_id, course_id, username, score, "issued", json.dumps(payload, ensure_ascii=False), now, now),
            )
        return self._certificate_for(username, course_id)

    def _learner_overview(self) -> list[dict[str, Any]]:
        learners: list[dict[str, Any]] = []
        for user in self.repository.list_users():
            if str(user.get("role") or "") != "student":
                continue
            for course in self._catalog_courses():
                session = type(
                    "CurriculumSession",
                    (),
                    {
                        "username": user["username"],
                        "is_teacher": False,
                        "permissions": {"curriculum.use": True},
                        "group_ids": [group["group_id"] for group in self.repository.list_user_groups(user["username"])],
                    },
                )()
                payload = self._course_payload(session, course)
                learners.append(
                    {
                        "username": user["username"],
                        "display_name": user["display_name"],
                        "course_id": course["course_id"],
                        "course_title": course["title"],
                        "release_enabled": bool(payload["release"]["enabled"]),
                        "passed_modules": payload["progress"]["passed_modules"],
                        "total_modules": payload["progress"]["total_modules"],
                        "final_passed": bool(payload["progress"]["final_passed"]),
                        "certified": bool(payload["progress"]["certified"]),
                    }
                )
        return learners

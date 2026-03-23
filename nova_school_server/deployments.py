from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
import zipfile
from pathlib import Path
from typing import Any

from .config import ServerConfig
from .database import SchoolRepository
from .project_files import copy_project_snapshot
from .workspace import WorkspaceManager


class DeploymentService:
    def __init__(self, repository: SchoolRepository, workspace_manager: WorkspaceManager, security_plane: Any, config: ServerConfig) -> None:
        self.repository = repository
        self.workspace_manager = workspace_manager
        self.security_plane = security_plane
        self.config = config
        self.share_root = config.data_path / "public_shares"
        self.export_root = config.data_path / "exports"
        self.share_root.mkdir(parents=True, exist_ok=True)
        self.export_root.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def list_artifacts(self, session: Any) -> list[dict[str, Any]]:
        query = "SELECT artifact_id FROM deployment_artifacts WHERE owner_username=? ORDER BY created_at DESC"
        params: tuple[Any, ...] = (session.username,)
        if session.is_teacher:
            query = "SELECT artifact_id FROM deployment_artifacts ORDER BY created_at DESC"
            params = ()
        with self.repository._lock:
            rows = self.repository._conn.execute(query, params).fetchall()
        return [self._artifact_payload(str(row["artifact_id"])) for row in rows]

    def create_share(self, session: Any, project: dict[str, Any]) -> dict[str, Any]:
        self._enforce_quota("max_active_shares")
        artifact_id = uuid.uuid4().hex[:12]
        public_root = self.share_root / artifact_id
        copied_files = copy_project_snapshot(self.workspace_manager.project_root(project), public_root)
        if "index.html" not in copied_files:
            raise ValueError("Web-Freigaben benoetigen eine index.html im Projektwurzelverzeichnis.")
        metadata = {"files": copied_files, "entry_path": "index.html", "runtime": project["runtime"], "kind": "share"}
        self._store_artifact(
            artifact_id=artifact_id,
            project=project,
            owner_username=session.username,
            kind="share",
            status="ready",
            relative_path=f"public_shares/{artifact_id}",
            label=f"Share {project['name']}",
            metadata=metadata,
        )
        return self._artifact_payload(artifact_id)

    def create_export(self, session: Any, project: dict[str, Any]) -> dict[str, Any]:
        self._enforce_quota("max_export_artifacts")
        artifact_id = uuid.uuid4().hex[:12]
        zip_path = self.export_root / f"{artifact_id}.zip"
        runtime = str(project["runtime"] or "python")
        with tempfile.TemporaryDirectory() as tmp_dir:
            bundle_root = Path(tmp_dir) / "bundle"
            source_root = bundle_root / "source"
            copy_project_snapshot(self.workspace_manager.project_root(project), source_root)
            build_result = self._prepare_bundle(runtime, project, source_root, bundle_root)
            with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for path in bundle_root.rglob("*"):
                    if path.is_file():
                        archive.write(path, path.relative_to(bundle_root).as_posix())
        metadata = {"runtime": runtime, **build_result, "download_name": zip_path.name}
        self._store_artifact(
            artifact_id=artifact_id,
            project=project,
            owner_username=session.username,
            kind="export",
            status="ready",
            relative_path=f"exports/{zip_path.name}",
            label=f"Export {project['name']}",
            metadata=metadata,
        )
        return self._artifact_payload(artifact_id)

    def resolve_share_path(self, artifact_id: str, relative_path: str) -> Path:
        artifact = self._artifact_row(artifact_id)
        if artifact is None or artifact["kind"] != "share":
            raise FileNotFoundError("Freigabe nicht gefunden.")
        root = self.config.data_path / str(artifact["relative_path"])
        target = (root / relative_path).resolve(strict=False)
        if not target.is_relative_to(root.resolve(strict=False)):
            raise PermissionError("Ungueltiger Share-Pfad.")
        return target if target.exists() else root / "index.html"

    def resolve_download_path(self, artifact_id: str) -> Path:
        artifact = self._artifact_row(artifact_id)
        if artifact is None or artifact["kind"] != "export":
            raise FileNotFoundError("Export nicht gefunden.")
        return self.config.data_path / str(artifact["relative_path"])

    def _prepare_bundle(self, runtime: str, project: dict[str, Any], source_root: Path, bundle_root: Path) -> dict[str, Any]:
        notes: list[str] = []
        build_artifacts: list[str] = []
        build_success = True
        bin_root = bundle_root / "artifacts"
        bin_root.mkdir(parents=True, exist_ok=True)
        self._write_runtime_guides(runtime, project, bundle_root)

        try:
            if runtime == "cpp":
                compiler = shutil.which("g++") or shutil.which("clang++")
                if compiler:
                    output = bin_root / ("program.exe" if os.name == "nt" else "program")
                    subprocess.run([compiler, "-std=c++20", "-O2", str(source_root / project["main_file"]), "-o", str(output)], check=True, capture_output=True, text=True)
                    build_artifacts.append(output.relative_to(bundle_root).as_posix())
                    notes.append("C++-Binary wurde vorkompiliert.")
                else:
                    build_success = False
                    notes.append("Kein C++-Compiler verfuegbar; Export enthaelt nur den Quellcode.")
            elif runtime == "java":
                javac = shutil.which("javac")
                if javac:
                    classes_root = bin_root / "classes"
                    classes_root.mkdir(parents=True, exist_ok=True)
                    subprocess.run([javac, "-d", str(classes_root), str(source_root / project["main_file"])], check=True, capture_output=True, text=True)
                    build_artifacts.extend(path.relative_to(bundle_root).as_posix() for path in classes_root.rglob("*") if path.is_file())
                    notes.append("Java-Klassen wurden vorkompiliert.")
                else:
                    build_success = False
                    notes.append("Kein JDK verfuegbar; Export enthaelt nur den Quellcode.")
            elif runtime == "rust":
                cargo_toml = source_root / "Cargo.toml"
                if cargo_toml.exists() and shutil.which("cargo"):
                    subprocess.run(["cargo", "build", "--release"], cwd=str(source_root), check=True, capture_output=True, text=True)
                    target_root = source_root / "target" / "release"
                    for path in target_root.iterdir():
                        if path.is_file() and path.suffix.lower() in {"", ".exe"}:
                            destination = bin_root / path.name
                            shutil.copy2(path, destination)
                            build_artifacts.append(destination.relative_to(bundle_root).as_posix())
                    notes.append("Rust-Binary wurde im Release-Modus gebaut.")
                elif shutil.which("rustc"):
                    output = bin_root / ("program.exe" if os.name == "nt" else "program")
                    subprocess.run(["rustc", str(source_root / project["main_file"]), "-o", str(output)], check=True, capture_output=True, text=True)
                    build_artifacts.append(output.relative_to(bundle_root).as_posix())
                    notes.append("Rust-Einzeldatei wurde kompiliert.")
                else:
                    build_success = False
                    notes.append("Keine Rust-Toolchain verfuegbar; Export enthaelt nur den Quellcode.")
            elif runtime in {"python", "node", "javascript", "html"}:
                notes.append("Der Export ist als Source-Bundle mit Startskripten vorbereitet.")
            else:
                notes.append("Der Export enthaelt den Projektstand als Source-Bundle.")
        except subprocess.CalledProcessError as exc:
            build_success = False
            (bundle_root / "BUILD_ERROR.txt").write_text((exc.stdout or "") + "\n" + (exc.stderr or ""), encoding="utf-8")
            build_artifacts.append("BUILD_ERROR.txt")
            notes.append("Die Build-Stufe ist fehlgeschlagen; Details stehen in BUILD_ERROR.txt.")

        return {"build_success": build_success, "notes": notes, "artifacts": build_artifacts}

    def _write_runtime_guides(self, runtime: str, project: dict[str, Any], bundle_root: Path) -> None:
        instructions = {
            "python": f"python source/{project['main_file']}",
            "javascript": f"node source/{project['main_file']}",
            "node": "npm install && npm run start",
            "html": "index.html direkt im Browser oeffnen oder per lokalem Webserver ausliefern",
            "cpp": f"g++ -std=c++20 -O2 source/{project['main_file']} -o program",
            "java": f"javac -d classes source/{project['main_file']} && java -cp classes {Path(str(project['main_file'])).stem}",
            "rust": "cargo run --release oder rustc source/main.rs -o program",
        }
        (bundle_root / "README_EXPORT.txt").write_text(
            "\n".join(
                [
                    f"Nova School Export fuer {project['name']}",
                    "",
                    f"Runtime: {runtime}",
                    f"Empfohlener Start: {instructions.get(runtime, 'Projektquellen im Ordner source nutzen.')}",
                    "",
                    "Der Ordner source enthaelt den eingefrorenen Projektstand.",
                ]
            ),
            encoding="utf-8",
        )

    def _store_artifact(
        self,
        *,
        artifact_id: str,
        project: dict[str, Any],
        owner_username: str,
        kind: str,
        status: str,
        relative_path: str,
        label: str,
        metadata: dict[str, Any],
    ) -> None:
        now = time.time()
        with self.repository._lock, self.repository._conn:
            self.repository._conn.execute(
                """
                INSERT INTO deployment_artifacts(
                    artifact_id, project_id, project_name, owner_username, kind, status, label, relative_path, metadata_json, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    artifact_id,
                    project["project_id"],
                    project["name"],
                    owner_username,
                    kind,
                    status,
                    label,
                    relative_path,
                    json.dumps(metadata, ensure_ascii=False),
                    now,
                    now,
                ),
            )

    def _init_schema(self) -> None:
        with self.repository._lock, self.repository._conn:
            self.repository._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS deployment_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    owner_username TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL,
                    label TEXT NOT NULL,
                    relative_path TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_deployment_artifacts_owner
                ON deployment_artifacts(owner_username, created_at);
                """
            )

    def _artifact_row(self, artifact_id: str) -> dict[str, Any] | None:
        with self.repository._lock:
            row = self.repository._conn.execute("SELECT * FROM deployment_artifacts WHERE artifact_id=?", (artifact_id,)).fetchone()
        return dict(row) if row is not None else None

    def _artifact_payload(self, artifact_id: str) -> dict[str, Any]:
        artifact = self._artifact_row(artifact_id)
        if artifact is None:
            raise FileNotFoundError("Deployment-Artefakt nicht gefunden.")
        metadata = json.loads(artifact["metadata_json"] or "{}")
        payload = {
            "artifact_id": artifact_id,
            "project_id": artifact["project_id"],
            "project_name": artifact["project_name"],
            "kind": artifact["kind"],
            "status": artifact["status"],
            "label": artifact["label"],
            "created_at": artifact["created_at"],
            "metadata": metadata,
        }
        if artifact["kind"] == "share":
            payload["url"] = f"/share/{artifact_id}/index.html"
        if artifact["kind"] == "export":
            payload["download_url"] = f"/download/{artifact_id}"
        return payload

    def _enforce_quota(self, quota_key: str) -> None:
        tenant = self.security_plane.get_tenant(self.config.tenant_id) or {}
        quotas = tenant.get("quotas") or {}
        limit = int(quotas.get(quota_key) or 0)
        if limit <= 0:
            return
        with self.repository._lock:
            row = self.repository._conn.execute("SELECT COUNT(*) AS count FROM deployment_artifacts").fetchone()
        if row is not None and int(row["count"]) >= limit:
            raise PermissionError(f"Quota erreicht: {quota_key}")

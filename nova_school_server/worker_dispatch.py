from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import shutil
import socket
import time
import zipfile
from pathlib import Path
from typing import Any

from .config import ServerConfig
from .database import SchoolRepository
from .workspace import WorkspaceManager


_IGNORED_ARTIFACT_NAMES = {"__pycache__", ".git", ".venv", "venv", "node_modules", "dist", "build", "target", ".nova-school"}


class RemoteWorkerDispatchService:
    HEARTBEAT_STALE_SECONDS = 20.0
    REQUEST_SKEW_SECONDS = 90

    def __init__(
        self,
        repository: SchoolRepository,
        workspace_manager: WorkspaceManager,
        security_plane: Any,
        config: ServerConfig,
    ) -> None:
        self.repository = repository
        self.workspace_manager = workspace_manager
        self.security_plane = security_plane
        self.config = config
        self.dispatch_root = config.data_path / "worker_dispatch"
        self.dispatch_root.mkdir(parents=True, exist_ok=True)

    def issue_bootstrap(
        self,
        *,
        worker_id: str,
        display_name: str,
        capabilities: list[str] | tuple[str, ...] | set[str] | None = None,
        labels: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        worker_capabilities = sorted({*(str(item) for item in (capabilities or [])), "playground.run"})
        token = secrets.token_urlsafe(32)
        secret_name = self._secret_name(worker_id)
        if hasattr(self.security_plane, "store_secret"):
            self.security_plane.store_secret(
                self.config.tenant_id,
                secret_name,
                token,
                metadata={"managed_by": "nova-school", "worker_id": worker_id},
            )
        self._ensure_worker_enrollment(
            worker_id,
            capabilities=worker_capabilities,
            labels=labels or {},
            metadata=metadata or {},
        )
        worker = self.repository.upsert_worker_node(
            worker_id,
            display_name or worker_id,
            secret_name,
            status="provisioned",
            capabilities=worker_capabilities,
            labels=labels or {},
            metadata=metadata or {},
        )
        return {
            "worker": worker,
            "bootstrap": {
                "server_url": self.server_base_url(),
                "worker_id": worker_id,
                "token": token,
                "tenant_id": self.config.tenant_id,
            },
        }

    def authenticate_worker(self, worker_id: str, token: str) -> dict[str, Any]:
        worker = self.repository.get_worker_node(worker_id)
        if worker is None:
            raise PermissionError("Worker ist nicht registriert.")
        secret = self._resolve_secret(worker["token_secret_name"])
        if secret is None or not secrets.compare_digest(str(secret), str(token)):
            raise PermissionError("Worker-Authentifizierung fehlgeschlagen.")
        return worker

    def verify_worker_request(
        self,
        worker_id: str,
        token: str,
        *,
        method: str,
        path: str,
        body: bytes,
        timestamp: str,
        nonce: str,
        signature: str,
    ) -> dict[str, Any]:
        worker = self.authenticate_worker(worker_id, token)
        if not timestamp or not nonce or not signature:
            raise PermissionError("Worker-Signaturdaten fehlen.")
        try:
            issued_at = int(timestamp)
        except ValueError as exc:
            raise PermissionError("Ungueltiger Worker-Zeitstempel.") from exc
        if abs(int(time.time()) - issued_at) > self.REQUEST_SKEW_SECONDS:
            raise PermissionError("Worker-Anfrage liegt ausserhalb des Replay-Fensters.")
        expected = self.build_worker_signature(
            secret=str(self._resolve_secret(worker["token_secret_name"]) or ""),
            method=method,
            path=path,
            body=body,
            timestamp=timestamp,
            nonce=nonce,
        )
        if not hmac.compare_digest(expected, signature):
            raise PermissionError("Worker-Signatur ist ungueltig.")
        if not self.repository.register_worker_nonce(worker_id, nonce, ttl_seconds=self.REQUEST_SKEW_SECONDS * 2):
            raise PermissionError("Replay erkannt: Nonce wurde bereits verwendet.")
        return worker

    def heartbeat(
        self,
        worker_id: str,
        *,
        endpoint_url: str = "",
        advertise_host: str = "",
        status: str = "active",
        metadata: dict[str, Any] | None = None,
        active_job_id: str = "",
    ) -> dict[str, Any]:
        worker = self.repository.get_worker_node(worker_id)
        if worker is None:
            raise FileNotFoundError("Worker ist nicht registriert.")
        effective_status = "busy" if active_job_id else (status or "active")
        updated = self.repository.upsert_worker_node(
            worker_id,
            worker["display_name"],
            worker["token_secret_name"],
            status=effective_status,
            endpoint_url=endpoint_url or str(worker.get("endpoint_url") or ""),
            advertise_host=advertise_host or str(worker.get("advertise_host") or ""),
            capabilities=list(worker.get("capabilities") or []),
            labels=dict(worker.get("labels") or {}),
            metadata={**dict(worker.get("metadata") or {}), **dict(metadata or {})},
            last_seen_at=time.time(),
        )
        stop_jobs = [
            job["job_id"]
            for job in self.repository.list_dispatch_jobs(worker_id=worker_id, statuses=("claimed", "running", "cancel_requested"))
            if bool(job.get("stop_requested"))
        ]
        return {"worker": self._present_worker(updated), "stop_job_ids": stop_jobs}

    def list_workers(self) -> list[dict[str, Any]]:
        workers = []
        loads = self._worker_loads()
        for worker in self.repository.list_worker_nodes():
            payload = self._present_worker(worker)
            payload["active_job_count"] = loads.get(str(worker["worker_id"]), 0)
            workers.append(payload)
        return workers

    def eligible_workers(self, runtime: str) -> list[dict[str, Any]]:
        eligible: list[dict[str, Any]] = []
        for worker in self.list_workers():
            if not bool(worker.get("online")):
                continue
            capabilities = {str(item) for item in list(worker.get("capabilities") or [])}
            labels = dict(worker.get("labels") or {})
            if "playground.run" not in capabilities:
                continue
            runtime_capability = f"runtime:{runtime}"
            declared_runtime_caps = {item for item in capabilities if item.startswith("runtime:")}
            if declared_runtime_caps and runtime_capability not in declared_runtime_caps and "runtime:*" not in declared_runtime_caps:
                continue
            runtime_labels = {str(labels.get("runtime") or ""), str(labels.get("language") or "")}
            if any(runtime_labels) and runtime not in runtime_labels and "*" not in runtime_labels:
                continue
            if not str(worker.get("advertise_host") or "").strip():
                continue
            eligible.append(worker)
        eligible.sort(key=lambda item: (int(item.get("active_job_count") or 0), str(item.get("display_name") or item["worker_id"])))
        return eligible

    def assign_workers(self, services: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        loads = self._worker_loads()
        assignments: dict[str, dict[str, Any]] = {}
        for service in services:
            candidates = self.eligible_workers(str(service["runtime"]))
            if not candidates:
                raise RuntimeError(f"Kein aktiver Remote-Worker fuer Runtime {service['runtime']} verfuegbar.")
            selected = min(
                candidates,
                key=lambda item: (loads.get(str(item["worker_id"]), 0), str(item.get("display_name") or item["worker_id"])),
            )
            assignments[str(service["name"])] = selected
            loads[str(selected["worker_id"])] = loads.get(str(selected["worker_id"]), 0) + 1
        return assignments

    def create_playground_job(
        self,
        *,
        worker_id: str,
        project: dict[str, Any],
        service: dict[str, Any],
        backend: str,
        payload: dict[str, Any],
        created_by: str,
        runtime_root: Path,
    ) -> dict[str, Any]:
        job = self.repository.create_dispatch_job(
            worker_id=worker_id,
            job_type="playground.service",
            project_id=str(project["project_id"]),
            service_name=str(service["name"]),
            runtime=str(service["runtime"]),
            backend=backend,
            payload=payload,
            created_by=created_by,
        )
        self._write_artifact(job["job_id"], runtime_root)
        return job

    def claim_next_job(self, worker_id: str) -> dict[str, Any] | None:
        job = self.repository.claim_next_dispatch_job(worker_id)
        if job is None:
            return None
        payload = dict(job)
        payload["artifact_url"] = f"{self.server_base_url()}/api/worker/jobs/{job['job_id']}/artifact"
        payload["issued_at"] = int(time.time())
        payload["job_signature"] = self.sign_job_payload(worker_id, payload)
        return payload

    def resolve_job_artifact(self, job_id: str) -> Path:
        target = self._job_root(job_id) / "payload.zip"
        if not target.exists():
            raise FileNotFoundError("Dispatch-Artefakt nicht gefunden.")
        return target

    def append_job_log(self, worker_id: str, job_id: str, chunk: str) -> dict[str, Any]:
        self._require_job_owner(worker_id, job_id)
        job = self.repository.append_dispatch_job_log(job_id, chunk)
        if job is None:
            raise FileNotFoundError("Dispatch-Job nicht gefunden.")
        return job

    def update_job_status(
        self,
        worker_id: str,
        job_id: str,
        *,
        status: str,
        result: dict[str, Any] | None = None,
        mark_started: bool = False,
        mark_finished: bool = False,
        clear_stop_request: bool = False,
    ) -> dict[str, Any]:
        self._require_job_owner(worker_id, job_id)
        job = self.repository.update_dispatch_job_status(
            job_id,
            status=status,
            result=result,
            mark_started=mark_started,
            mark_finished=mark_finished,
            clear_stop_request=clear_stop_request,
        )
        if job is None:
            raise FileNotFoundError("Dispatch-Job nicht gefunden.")
        return job

    def request_stop(self, job_id: str) -> dict[str, Any] | None:
        job = self.repository.get_dispatch_job(job_id)
        if job is None:
            return None
        if str(job.get("status") or "") == "queued":
            return self.repository.update_dispatch_job_status(
                job_id,
                status="stopped",
                result={"reason": "vor dem Claim gestoppt"},
                mark_finished=True,
                clear_stop_request=True,
            )
        self.repository.request_dispatch_job_stop(job_id)
        return self.repository.update_dispatch_job_status(job_id, status="cancel_requested")

    def latest_jobs_for_project(self, project_id: str) -> dict[str, dict[str, Any]]:
        return {
            str(job["service_name"]): job
            for job in self.repository.list_latest_dispatch_jobs_for_project(project_id)
        }

    def sign_job_payload(self, worker_id: str, payload: dict[str, Any]) -> str:
        worker = self.repository.get_worker_node(worker_id)
        if worker is None:
            raise FileNotFoundError("Worker ist nicht registriert.")
        secret = str(self._resolve_secret(worker["token_secret_name"]) or "")
        canonical = json.dumps(self._job_signature_payload(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()

    @staticmethod
    def build_worker_signature(*, secret: str, method: str, path: str, body: bytes, timestamp: str, nonce: str) -> str:
        body_hash = hashlib.sha256(body or b"").hexdigest()
        canonical = "\n".join([method.upper(), path, timestamp, nonce, body_hash]).encode("utf-8")
        return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()

    def server_base_url(self) -> str:
        host = str(self.repository.get_setting("server_public_host", "") or "").strip()
        if not host:
            configured = str(self.config.host or "").strip()
            host = configured if configured not in {"", "0.0.0.0", "::"} else (self._guess_lan_ipv4() or "127.0.0.1")
        return f"http://{host}:{self.config.port}"

    def _present_worker(self, worker: dict[str, Any]) -> dict[str, Any]:
        payload = dict(worker)
        payload["online"] = self._is_online(worker)
        if not payload["online"] and payload["status"] not in {"provisioned"}:
            payload["status"] = "offline"
        enrollment = self._worker_enrollment(str(worker["worker_id"]))
        payload["enrollment"] = enrollment
        return payload

    def _is_online(self, worker: dict[str, Any]) -> bool:
        last_seen = float(worker.get("last_seen_at") or 0.0)
        return last_seen > 0 and (time.time() - last_seen) <= self.HEARTBEAT_STALE_SECONDS

    def _worker_loads(self) -> dict[str, int]:
        loads: dict[str, int] = {}
        for job in self.repository.list_dispatch_jobs(statuses=("queued", "claimed", "running", "cancel_requested")):
            worker_id = str(job["worker_id"])
            loads[worker_id] = loads.get(worker_id, 0) + 1
        return loads

    def _ensure_worker_enrollment(
        self,
        worker_id: str,
        *,
        capabilities: list[str],
        labels: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        if self._worker_enrollment(worker_id) is not None:
            return
        if hasattr(self.security_plane, "onboard_worker"):
            self.security_plane.onboard_worker(
                worker_id,
                self.config.tenant_id,
                namespace="school-runtime",
                capabilities=set(capabilities),
                labels=labels,
                metadata=metadata,
            )

    def _worker_enrollment(self, worker_id: str) -> dict[str, Any] | None:
        if not hasattr(self.security_plane, "list_worker_enrollments"):
            return None
        workers = list(self.security_plane.list_worker_enrollments(self.config.tenant_id))
        return next((item for item in workers if str(item.get("worker_id") or "") == worker_id), None)

    def _resolve_secret(self, secret_name: str) -> str | None:
        if not hasattr(self.security_plane, "resolve_secret"):
            return None
        secret = self.security_plane.resolve_secret(self.config.tenant_id, secret_name)
        if secret is None:
            return None
        return str(secret.get("secret_value") or "")

    def _require_job_owner(self, worker_id: str, job_id: str) -> dict[str, Any]:
        job = self.repository.get_dispatch_job(job_id)
        if job is None:
            raise FileNotFoundError("Dispatch-Job nicht gefunden.")
        if str(job["worker_id"]) != str(worker_id):
            raise PermissionError("Dispatch-Job gehoert zu einem anderen Worker.")
        return job

    @staticmethod
    def _job_signature_payload(payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "job_id": payload.get("job_id"),
            "worker_id": payload.get("worker_id"),
            "job_type": payload.get("job_type"),
            "project_id": payload.get("project_id"),
            "service_name": payload.get("service_name"),
            "runtime": payload.get("runtime"),
            "backend": payload.get("backend"),
            "status": payload.get("status"),
            "payload": payload.get("payload"),
            "artifact_url": payload.get("artifact_url"),
            "issued_at": payload.get("issued_at"),
        }

    def _write_artifact(self, job_id: str, runtime_root: Path) -> None:
        job_root = self._job_root(job_id)
        if job_root.exists():
            shutil.rmtree(job_root)
        job_root.mkdir(parents=True, exist_ok=True)
        archive_path = job_root / "payload.zip"
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(runtime_root.rglob("*")):
                if not path.is_file():
                    continue
                if any(part in _IGNORED_ARTIFACT_NAMES for part in path.relative_to(runtime_root).parts):
                    continue
                archive.write(path, arcname=path.relative_to(runtime_root).as_posix())

    def _job_root(self, job_id: str) -> Path:
        return self.dispatch_root / "jobs" / job_id

    @staticmethod
    def _secret_name(worker_id: str) -> str:
        return f"worker-token:{worker_id}"

    @staticmethod
    def _guess_lan_ipv4() -> str | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
                probe.connect(("8.8.8.8", 80))
                ip = probe.getsockname()[0]
                return ip if ip and not ip.startswith("127.") else None
        except OSError:
            return None

from __future__ import annotations

import json
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from nova_school_server.collaboration import NotebookCollaborationService
from nova_school_server.code_runner import CodeRunner
from nova_school_server.config import ServerConfig
from nova_school_server.database import SchoolRepository
from nova_school_server.deployments import DeploymentService
from nova_school_server.distributed import DistributedPlaygroundService
from nova_school_server.mentor import SocraticMentorService
from nova_school_server.reviews import ReviewService
from nova_school_server.workspace import WorkspaceManager, slugify


class _FakeLMStudio:
    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    def complete(self, prompt: str, system_prompt: str, model: str | None = None) -> dict[str, str]:
        self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "model": model})
        return {"text": "Pruefe zuerst die Schleifenbedingung und die Array-Grenzen.", "model": model or "fake-mentor"}


class _FakeSecurityPlane:
    def __init__(self) -> None:
        self.secrets: dict[tuple[str, str], dict[str, object]] = {}
        self.tenants: dict[str, dict[str, object]] = {}
        self.cas: dict[str, dict[str, object]] = {}
        self.policies: dict[str, dict[str, object]] = {}
        self.workers: dict[str, dict[str, object]] = {}

    def resolve_secret(self, tenant_id: str, name: str) -> dict[str, object] | None:
        return self.secrets.get((tenant_id, name))

    def store_secret(self, tenant_id: str, name: str, secret_value: str, metadata=None) -> dict[str, object]:
        payload = {"tenant_id": tenant_id, "name": name, "secret_value": secret_value, "metadata": metadata or {}}
        self.secrets[(tenant_id, name)] = payload
        return payload

    def get_tenant(self, tenant_id: str) -> dict[str, object] | None:
        return self.tenants.get(tenant_id, {"tenant_id": tenant_id, "quotas": {}})

    def create_certificate_authority(self, name: str, common_name: str) -> dict[str, object]:
        payload = {"name": name, "common_name": common_name}
        self.cas[name] = payload
        return payload

    def get_certificate_authority(self, name: str) -> dict[str, object] | None:
        return self.cas.get(name)

    def set_trust_policy(self, name: str, **payload) -> dict[str, object]:
        policy = {"name": name, **payload}
        self.policies[name] = policy
        return policy

    def get_trust_policy(self, name: str) -> dict[str, object] | None:
        return self.policies.get(name)

    def onboard_worker(self, worker_id: str, tenant_id: str, **payload) -> dict[str, object]:
        worker = {"worker_id": worker_id, "tenant_id": tenant_id, **payload}
        self.workers[worker_id] = worker
        return worker

    def list_worker_enrollments(self, tenant_id: str) -> list[dict[str, object]]:
        return [worker for worker in self.workers.values() if worker["tenant_id"] == tenant_id]


class _Session:
    def __init__(self, username: str, role: str = "student", *, display_name: str | None = None, group_ids: list[str] | None = None) -> None:
        self.username = username
        self.role = role
        self.user = {"username": username, "display_name": display_name or username.title()}
        self.groups = [{"group_id": group_id, "display_name": group_id} for group_id in (group_ids or [])]

    @property
    def is_teacher(self) -> bool:
        return self.role in {"teacher", "admin"}

    @property
    def group_ids(self) -> list[str]:
        return [group["group_id"] for group in self.groups]


class _FakeToolSandbox:
    def authorize(self, *_args, **_kwargs):  # pragma: no cover
        return {}


class GoldFeatureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base_path = Path(self.tmp.name)
        self.config = ServerConfig.from_base_path(self.base_path)
        self.repository = SchoolRepository(self.config.database_path)
        self.workspace = WorkspaceManager(self.config)
        self.security = _FakeSecurityPlane()
        self.lmstudio = _FakeLMStudio()
        self.runner = CodeRunner(self.config, _FakeToolSandbox(), self.workspace, self.repository)

    def tearDown(self) -> None:
        self.repository.close()
        self.tmp.cleanup()

    def _create_user(self, username: str, role: str = "student", *, display_name: str | None = None) -> dict[str, object]:
        return self.repository.create_user(
            username=username,
            display_name=display_name or username.title(),
            password_hash="hash",
            password_salt="salt",
            role=role,
        )

    def _create_project(self, *, owner_type: str, owner_key: str, template: str, name: str, created_by: str = "admin") -> dict[str, object]:
        project = self.repository.create_project(
            owner_type=owner_type,
            owner_key=owner_key,
            name=name,
            slug=slugify(name),
            template=template,
            runtime={"frontend-lab": "html", "distributed-system": "python"}.get(template, template),
            main_file={"frontend-lab": "index.html", "distributed-system": "services/coordinator.py"}.get(template, "main.py"),
            description=f"Testprojekt {name}",
            created_by=created_by,
        )
        self.workspace.materialize_project(project)
        return project

    def test_collaboration_merges_parallel_cell_changes(self) -> None:
        self._create_user("alice")
        self._create_user("bob")
        project = self._create_project(owner_type="user", owner_key="alice", template="python", name="Collab Python")
        service = NotebookCollaborationService(self.repository, self.workspace)

        initial = service.snapshot(project)
        base_cells = list(initial["cells"])
        session_a = _Session("alice", display_name="Alice")
        session_b = _Session("bob", display_name="Bob")

        cells_a = [*base_cells, {"id": "cell-a", "title": "A", "language": "python", "code": "print('A')", "stdin": "", "output": ""}]
        payload_a = service.sync(session_a, project, cells_a, base_revision=initial["revision"])
        self.assertEqual(payload_a["revision"], 1)

        cells_b = [*base_cells, {"id": "cell-b", "title": "B", "language": "python", "code": "print('B')", "stdin": "", "output": ""}]
        payload_b = service.sync(session_b, project, cells_b, base_revision=initial["revision"])

        cell_ids = [cell["id"] for cell in payload_b["cells"]]
        self.assertIn("cell-a", cell_ids)
        self.assertIn("cell-b", cell_ids)
        self.assertGreaterEqual(payload_b["revision"], 2)

    def test_mentor_persists_thread_and_teacher_can_inspect(self) -> None:
        self._create_user("student")
        self._create_user("teacher", role="teacher")
        project = self._create_project(owner_type="user", owner_key="student", template="python", name="Mentor Python")
        service = SocraticMentorService(self.repository, self.lmstudio)

        reply = service.ask(
            _Session("student", display_name="Schueler"),
            project,
            prompt="Warum scheitert meine Schleife?",
            code="for i in range(len(values)+1): print(values[i])",
            path_hint="main.py",
            run_output="IndexError: list index out of range",
        )

        self.assertIn("Schleifenbedingung", reply["reply"])
        thread = service.thread(_Session("teacher", role="teacher", display_name="Lehrer"), project, username="student")
        self.assertEqual(len(thread), 2)
        self.assertEqual(thread[-1]["role"], "assistant")

    def test_review_submission_feedback_and_deployment_artifacts_work(self) -> None:
        self._create_user("student")
        self._create_user("reviewer")
        self.repository.create_group("class-a", "Class A")
        self.repository.add_membership("student", "class-a")
        self.repository.add_membership("reviewer", "class-a")
        project = self._create_project(owner_type="user", owner_key="student", template="frontend-lab", name="Portfolio")

        review_service = ReviewService(self.repository, self.security, self.workspace, self.config.tenant_id, self.config.data_path / "review_submissions")
        deploy_service = DeploymentService(self.repository, self.workspace, self.security, self.config)

        self.repository.add_audit("student", "project.run", "project", str(project["project_id"]), {"returncode": 1})
        self.repository.add_audit("student", "project.run", "project", str(project["project_id"]), {"returncode": 0})

        submission = review_service.submit(_Session("student", group_ids=["class-a"]), project)
        self.assertEqual(submission["assigned_count"], 1)
        self.assertIn("index.html", submission["files"])

        dashboard = review_service.dashboard(_Session("reviewer", group_ids=["class-a"]))
        assignment_id = dashboard["assignments"][0]["assignment_id"]
        assignment = review_service.submit_feedback(
            _Session("reviewer", group_ids=["class-a"]),
            assignment_id,
            {"summary": "Sauber strukturiert", "strengths": "Klare HTML-Struktur", "risks": "Keine", "questions": "Keine", "score": 5},
        )
        self.assertEqual(assignment["status"], "completed")

        share = deploy_service.create_share(_Session("student"), project)
        export = deploy_service.create_export(_Session("student"), project)
        self.assertTrue((self.config.data_path / "public_shares" / share["artifact_id"] / "index.html").exists())
        export_path = deploy_service.resolve_download_path(export["artifact_id"])
        self.assertTrue(export_path.exists())
        with zipfile.ZipFile(export_path) as archive:
            self.assertIn("README_EXPORT.txt", archive.namelist())

    def test_distributed_playground_starts_and_stops_template_services(self) -> None:
        self._create_user("teacher", role="teacher")
        project = self._create_project(owner_type="user", owner_key="teacher", template="distributed-system", name="Playground")
        self.repository.put_setting("playground_dispatch_mode", "local")
        self.repository.put_setting("runner_backend", "process")
        self.repository.put_setting("unsafe_process_backend_enabled", True)
        service = DistributedPlaygroundService(self.repository, self.workspace, self.security, self.config, runner=self.runner)
        session = _Session("teacher", role="teacher")

        try:
            status = service.status(project)
            self.assertEqual(len(status["services"]), 3)
            self.assertIsNotNone(status["certificate_authority"])
            self.assertIsNotNone(status["trust_policy"])

            started = service.start(session, project)
            time.sleep(1.0)
            self.assertTrue(any(item["running"] for item in started["services"]))
            stopped = service.stop(session, project)
            self.assertTrue(all(not item["running"] for item in stopped["services"]))
        finally:
            service.close()

    def test_distributed_playground_dispatches_remote_jobs_to_registered_workers(self) -> None:
        self._create_user("teacher", role="teacher")
        project = self._create_project(owner_type="user", owner_key="teacher", template="distributed-system", name="Remote Playground")
        self.repository.put_setting("playground_dispatch_mode", "worker")
        self.repository.put_setting("runner_backend", "container")
        self.repository.put_setting("container_oci_runtime", "runsc")
        service = DistributedPlaygroundService(self.repository, self.workspace, self.security, self.config, runner=self.runner)
        session = _Session("teacher", role="teacher")

        bootstrap = service.dispatch.issue_bootstrap(
            worker_id="lab-node-01",
            display_name="Lab Node 01",
            capabilities=["runtime:python"],
            labels={"runtime": "python"},
        )
        token = str(bootstrap["bootstrap"]["token"])
        authenticated = service.dispatch.authenticate_worker("lab-node-01", token)
        self.assertEqual(authenticated["worker_id"], "lab-node-01")
        service.dispatch.heartbeat("lab-node-01", advertise_host="192.168.178.81", status="active")

        with patch("nova_school_server.distributed.subprocess.Popen", side_effect=AssertionError("local process launch is not allowed in worker mode")):
            started = service.start(session, project)

        self.assertEqual(started["dispatch_mode"], "worker")
        self.assertEqual(len(started["services"]), 3)
        self.assertTrue(all(item["job_status"] == "queued" for item in started["services"]))
        self.assertTrue(all(item["worker_id"] == "lab-node-01" for item in started["services"]))

        jobs = self.repository.list_dispatch_jobs(project_id=str(project["project_id"]))
        self.assertEqual(len(jobs), 3)
        self.assertEqual(str(jobs[0]["payload"].get("container_oci_runtime") or ""), "runsc")
        claim = service.dispatch.claim_next_job("lab-node-01")
        self.assertIsNotNone(claim)
        assert claim is not None
        self.assertIn("/api/worker/jobs/", claim["artifact_url"])
        self.assertTrue(claim["job_signature"])
        self.assertEqual(claim["job_signature"], service.dispatch.sign_job_payload("lab-node-01", claim))

        service.dispatch.update_job_status("lab-node-01", str(claim["job_id"]), status="running", mark_started=True)
        stopped = service.stop(session, project, service_names=["coordinator"])
        coordinator = next(item for item in stopped["services"] if item["name"] == "coordinator")
        self.assertEqual(coordinator["job_status"], "cancel_requested")

    def test_worker_request_signature_rejects_replay(self) -> None:
        service = DistributedPlaygroundService(self.repository, self.workspace, self.security, self.config, runner=self.runner)
        bootstrap = service.dispatch.issue_bootstrap(
            worker_id="lab-node-02",
            display_name="Lab Node 02",
            capabilities=["runtime:python"],
            labels={"runtime": "python"},
        )
        token = str(bootstrap["bootstrap"]["token"])
        body = json.dumps({"status": "active"}, ensure_ascii=False).encode("utf-8")
        timestamp = str(int(time.time()))
        nonce = "nonce-1"
        signature = service.dispatch.build_worker_signature(
            secret=token,
            method="POST",
            path="/api/worker/heartbeat",
            body=body,
            timestamp=timestamp,
            nonce=nonce,
        )
        worker = service.dispatch.verify_worker_request(
            "lab-node-02",
            token,
            method="POST",
            path="/api/worker/heartbeat",
            body=body,
            timestamp=timestamp,
            nonce=nonce,
            signature=signature,
        )
        self.assertEqual(worker["worker_id"], "lab-node-02")
        with self.assertRaises(PermissionError):
            service.dispatch.verify_worker_request(
                "lab-node-02",
                token,
                method="POST",
                path="/api/worker/heartbeat",
                body=body,
                timestamp=timestamp,
                nonce=nonce,
                signature=signature,
            )


if __name__ == "__main__":
    unittest.main()

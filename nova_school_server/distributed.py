from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .code_runner import CodeRunner
from .config import ServerConfig
from .database import SchoolRepository
from .worker_dispatch import RemoteWorkerDispatchService
from .workspace import WorkspaceManager


@dataclass
class _ManagedWorker:
    process: subprocess.Popen[str]
    command: list[str]
    log_path: Path
    worker_id: str
    runtime: str
    backend: str
    port: int
    started_at: float
    container_name: str = ""
    network_name: str = ""
    runtime_root: Path | None = None
    container_runtime: str = ""


class DistributedPlaygroundService:
    def __init__(self, repository: SchoolRepository, workspace_manager: WorkspaceManager, security_plane: Any, config: ServerConfig, runner: CodeRunner | None = None) -> None:
        self.repository = repository
        self.workspace_manager = workspace_manager
        self.security_plane = security_plane
        self.config = config
        self.runner = runner
        self.dispatch = RemoteWorkerDispatchService(repository, workspace_manager, security_plane, config)
        self._clusters: dict[str, dict[str, _ManagedWorker]] = {}

    def close(self) -> None:
        for project_id in list(self._clusters):
            self.stop_project(project_id)

    def status(self, project: dict[str, Any]) -> dict[str, Any]:
        if self._dispatch_mode() == "local":
            return self._status_local(project)
        return self._status_remote(project)

    def _status_local(self, project: dict[str, Any]) -> dict[str, Any]:
        project_id = str(project["project_id"])
        topology = self._load_topology(project)
        self._ensure_security_assets(project_id, topology)
        services = []
        workers = self.security_plane.list_worker_enrollments(self.config.tenant_id)
        worker_lookup = {
            str(item["worker_id"]): item
            for item in workers
            if str(item.get("namespace") or "") == project_id
        }
        cluster = self._clusters.get(project_id, {})
        for service in topology["services"]:
            worker_id = f"{project_id}-{service['name']}"
            managed = cluster.get(service["name"])
            running = managed is not None and managed.process.poll() is None
            port = managed.port if managed is not None else int(service.get("port") or 0)
            services.append(
                {
                    "name": service["name"],
                    "runtime": service["runtime"],
                    "entrypoint": service["entrypoint"],
                    "port": port,
                    "url": f"http://127.0.0.1:{port}" if port else "",
                    "running": running,
                    "pid": managed.process.pid if managed is not None and running else None,
                    "worker_id": worker_id,
                    "backend": managed.backend if managed is not None else self._resolved_backend(None),
                    "worker": worker_lookup.get(worker_id),
                    "log_tail": self._tail_log(managed.log_path if managed is not None else self._log_path(project, service["name"])),
                    "command": managed.command if managed is not None else [],
                }
            )
        return {
            "project_id": project_id,
            "topology": topology,
            "services": services,
            "trust_policy": self.security_plane.get_trust_policy(self._policy_name(project_id)),
            "certificate_authority": self.security_plane.get_certificate_authority(self._ca_name(project_id)),
            "dispatch_mode": "local",
            "workers": self.dispatch.list_workers(),
        }

    def start(self, session: Any, project: dict[str, Any], *, service_names: list[str] | None = None) -> dict[str, Any]:
        if self._dispatch_mode() == "local":
            return self._start_local(session, project, service_names=service_names)
        return self._start_remote(session, project, service_names=service_names)

    def _start_local(self, session: Any, project: dict[str, Any], *, service_names: list[str] | None = None) -> dict[str, Any]:
        topology = self._load_topology(project)
        project_id = str(project["project_id"])
        backend = self._resolved_backend(session)
        self._ensure_security_assets(project_id, topology)
        cluster = self._clusters.setdefault(project_id, {})
        selected = {name for name in service_names or []}
        service_map = {service["name"]: service for service in topology["services"]}
        resolved_ports = self._resolve_ports(topology["services"], cluster)
        if backend == "container":
            self._ensure_network(project_id)

        for service in topology["services"]:
            if selected and service["name"] not in selected:
                continue
            if service["name"] in cluster:
                self._stop_worker(cluster.pop(service["name"]))
            worker_id = f"{project_id}-{service['name']}"
            runtime_root = self._prepare_service_workspace(project, service["name"])
            env = self._service_env(session, project, service_map, service, resolved_ports, worker_id, backend=backend)
            command = self._service_command(project, service, backend=backend, runtime_root=runtime_root, env=env, port=resolved_ports[service["name"]], worker_id=worker_id)
            log_path = self._log_path(project, service["name"])
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handle = log_path.open("w", encoding="utf-8")
            process = subprocess.Popen(
                command,
                cwd=str(runtime_root if backend == "process" else self.workspace_manager.project_root(project)),
                env=env if backend == "process" else dict(os.environ),
                stdout=handle,
                stderr=subprocess.STDOUT,
                text=True,
            )
            handle.close()
            cluster[service["name"]] = _ManagedWorker(
                process=process,
                command=command,
                log_path=log_path,
                worker_id=worker_id,
                runtime=service["runtime"],
                backend=backend,
                port=resolved_ports[service["name"]],
                started_at=time.time(),
                container_name=self._container_name(worker_id) if backend == "container" else "",
                network_name=self._network_name(project_id) if backend == "container" else "",
                runtime_root=runtime_root,
                container_runtime=self.runner._container_runtime({}) if backend == "container" and self.runner is not None else "",
            )
            self.repository.add_audit(session.username, "playground.start", "project", project_id, {"service": service["name"], "worker_id": worker_id, "backend": backend})
        return self.status(project)

    def stop(self, session: Any, project: dict[str, Any], *, service_names: list[str] | None = None) -> dict[str, Any]:
        if self._dispatch_mode() == "local":
            return self._stop_local(session, project, service_names=service_names)
        return self._stop_remote(session, project, service_names=service_names)

    def _stop_local(self, session: Any, project: dict[str, Any], *, service_names: list[str] | None = None) -> dict[str, Any]:
        project_id = str(project["project_id"])
        cluster = self._clusters.get(project_id, {})
        selected = {name for name in service_names or []}
        for name in list(cluster):
            if selected and name not in selected:
                continue
            worker = cluster.pop(name)
            self._stop_worker(worker)
            self.repository.add_audit(session.username, "playground.stop", "project", project_id, {"service": name, "worker_id": worker.worker_id})
        if not cluster and project_id in self._clusters:
            self._clusters.pop(project_id, None)
        if not cluster:
            self._remove_network(project_id)
        return self.status(project)

    def _status_remote(self, project: dict[str, Any]) -> dict[str, Any]:
        project_id = str(project["project_id"])
        topology = self._load_topology(project)
        self._ensure_security_assets(project_id, topology)
        workers = {str(item["worker_id"]): item for item in self.dispatch.list_workers()}
        jobs = self.dispatch.latest_jobs_for_project(project_id)
        services = []
        for service in topology["services"]:
            job = jobs.get(str(service["name"]))
            worker = workers.get(str(job["worker_id"])) if job is not None else None
            port = int(service.get("port") or 0)
            advertised_host = str((worker or {}).get("advertise_host") or "")
            status = str(job.get("status") or "idle") if job is not None else "idle"
            services.append(
                {
                    "name": service["name"],
                    "runtime": service["runtime"],
                    "entrypoint": service["entrypoint"],
                    "port": port,
                    "url": f"http://{advertised_host}:{port}" if advertised_host and port and status in {"queued", "claimed", "running", "cancel_requested", "completed"} else "",
                    "running": status in {"queued", "claimed", "running", "cancel_requested"},
                    "pid": (job or {}).get("result", {}).get("pid") if job is not None else None,
                    "worker_id": str(job["worker_id"]) if job is not None else "",
                    "backend": str(job["backend"]) if job is not None else self._resolved_backend(None),
                    "worker": worker,
                    "job_id": str(job["job_id"]) if job is not None else "",
                    "job_status": status,
                    "log_tail": str(job.get("log_tail") or "") if job is not None else "",
                    "command": list((job or {}).get("result", {}).get("command") or []),
                }
            )
        return {
            "project_id": project_id,
            "topology": topology,
            "services": services,
            "trust_policy": self.security_plane.get_trust_policy(self._policy_name(project_id)),
            "certificate_authority": self.security_plane.get_certificate_authority(self._ca_name(project_id)),
            "dispatch_mode": "worker",
            "workers": self.dispatch.list_workers(),
        }

    def _start_remote(self, session: Any, project: dict[str, Any], *, service_names: list[str] | None = None) -> dict[str, Any]:
        topology = self._load_topology(project)
        project_id = str(project["project_id"])
        backend = self._resolved_backend(session)
        self._ensure_security_assets(project_id, topology)
        selected = [service for service in topology["services"] if not service_names or service["name"] in set(service_names)]
        for service in selected:
            if int(service.get("port") or 0) <= 0:
                raise ValueError(f"Remote-Dispatch benoetigt einen expliziten Port fuer Service {service['name']}.")
        existing_jobs = self.dispatch.latest_jobs_for_project(project_id)
        assignments = self.dispatch.assign_workers(selected)
        service_map = {service["name"]: service for service in topology["services"]}
        known_workers = {str(item["worker_id"]): item for item in self.dispatch.list_workers()}
        service_urls: dict[str, str] = {}
        for name, worker in assignments.items():
            service_urls[name] = f"http://{worker['advertise_host']}:{int(service_map[name].get('port') or 0)}"
        for name, job in existing_jobs.items():
            if name in service_urls:
                continue
            worker = known_workers.get(str(job.get("worker_id") or ""))
            if worker is None or not str(worker.get("advertise_host") or "").strip():
                continue
            service_urls[name] = f"http://{worker['advertise_host']}:{int(service_map[name].get('port') or 0)}"
        for service in selected:
            existing = existing_jobs.get(str(service["name"]))
            if existing is not None and str(existing.get("status") or "") in {"queued", "claimed", "running", "cancel_requested"}:
                self.dispatch.request_stop(str(existing["job_id"]))
            runtime_root = self._prepare_service_workspace(project, service["name"])
            worker = assignments[service["name"]]
            env = self._service_env(
                session,
                project,
                service_map,
                service,
                {item["name"]: int(item.get("port") or 0) for item in topology["services"]},
                str(worker["worker_id"]),
                backend=backend,
            )
            env.update(
                {
                    "NOVA_PLAYGROUND_BIND_HOST": "0.0.0.0",
                    "NOVA_PLAYGROUND_URLS": json.dumps(
                        {
                            name: service_urls[name]
                            for name in service_urls
                        },
                        ensure_ascii=False,
                    ),
                }
            )
            payload = {
                "project_id": project_id,
                "project_name": str(project.get("name") or ""),
                "service_name": service["name"],
                "entrypoint": service["entrypoint"],
                "runtime": service["runtime"],
                "backend": backend,
                "port": int(service.get("port") or 0),
                "env": env,
                "worker_id": str(worker["worker_id"]),
            }
            if backend == "container" and self.runner is not None:
                payload.update(
                    {
                        "container_runtime": self.runner._container_runtime({}),
                        "container_oci_runtime": self.repository.get_setting("container_oci_runtime", ""),
                        "container_image": self.runner._container_image(self._service_language(service["runtime"]), {}),
                        "container_memory_limit": self.repository.get_setting("container_memory_limit", "512m"),
                        "container_cpu_limit": self.repository.get_setting("container_cpu_limit", "1.5"),
                        "container_pids_limit": self.repository.get_setting("container_pids_limit", "128"),
                        "container_file_size_limit_kb": self.repository.get_setting("container_file_size_limit_kb", 65536),
                        "container_nofile_limit": self.repository.get_setting("container_nofile_limit", 256),
                        "container_tmpfs_limit": self.repository.get_setting("container_tmpfs_limit", "64m"),
                    }
                )
            job = self.dispatch.create_playground_job(
                worker_id=str(worker["worker_id"]),
                project=project,
                service=service,
                backend=backend,
                payload=payload,
                created_by=session.username,
                runtime_root=runtime_root,
            )
            self.repository.add_audit(
                session.username,
                "playground.dispatch",
                "project",
                project_id,
                {
                    "service": service["name"],
                    "worker_id": worker["worker_id"],
                    "backend": backend,
                    "job_id": job["job_id"],
                },
            )
        return self.status(project)

    def _stop_remote(self, session: Any, project: dict[str, Any], *, service_names: list[str] | None = None) -> dict[str, Any]:
        project_id = str(project["project_id"])
        jobs = self.dispatch.latest_jobs_for_project(project_id)
        selected = {name for name in service_names or []}
        for name, job in jobs.items():
            if selected and name not in selected:
                continue
            if str(job.get("status") or "") not in {"queued", "claimed", "running", "cancel_requested"}:
                continue
            self.dispatch.request_stop(str(job["job_id"]))
            self.repository.add_audit(
                session.username,
                "playground.stop.request",
                "project",
                project_id,
                {"service": name, "worker_id": job["worker_id"], "job_id": job["job_id"]},
            )
        return self.status(project)

    def stop_project(self, project_id: str) -> None:
        cluster = self._clusters.pop(project_id, {})
        for worker in cluster.values():
            self._stop_worker(worker)
        self._remove_network(project_id)

    def _ensure_security_assets(self, project_id: str, topology: dict[str, Any]) -> None:
        if self.security_plane.get_certificate_authority(self._ca_name(project_id)) is None:
            self.security_plane.create_certificate_authority(self._ca_name(project_id), common_name=f"Nova School Playground {project_id}")
        if self.security_plane.get_trust_policy(self._policy_name(project_id)) is None:
            self.security_plane.set_trust_policy(
                self._policy_name(project_id),
                tenant_id=self.config.tenant_id,
                namespace=project_id,
                require_tls=False,
                capabilities={"playground.run"},
                metadata={"project_id": project_id, "managed_by": "nova-school"},
            )

    def _load_topology(self, project: dict[str, Any]) -> dict[str, Any]:
        topology_path = self.workspace_manager.project_root(project) / "topology.json"
        if not topology_path.exists():
            raise FileNotFoundError("topology.json fuer den Playground fehlt.")
        payload = json.loads(topology_path.read_text(encoding="utf-8"))
        services = []
        for index, raw in enumerate(list(payload.get("services") or [])):
            if not raw.get("name") or not raw.get("runtime") or not raw.get("entrypoint"):
                raise ValueError("Jeder Playground-Service benoetigt name, runtime und entrypoint.")
            services.append(
                {
                    "name": str(raw["name"]),
                    "runtime": str(raw["runtime"]).lower(),
                    "entrypoint": str(raw["entrypoint"]),
                    "port": int(raw.get("port") or 0),
                    "env": dict(raw.get("env") or {}),
                    "kind": str(raw.get("kind") or ("gateway" if index == 0 else "worker")),
                }
            )
        return {"namespace": str(payload.get("namespace") or "playground"), "services": services}

    def _service_env(
        self,
        session: Any,
        project: dict[str, Any],
        service_map: dict[str, dict[str, Any]],
        service: dict[str, Any],
        resolved_ports: dict[str, int],
        worker_id: str,
        *,
        backend: str,
    ) -> dict[str, str]:
        env = self.runner._execution_env(self._service_runtime_root(project, service["name"]), web_access=False) if self.runner is not None else dict(os.environ)
        port = resolved_ports[service["name"]]
        service_urls = {
            name: (
                f"http://{name}:{int(service_map[name].get('port') or resolved_ports[name])}"
                if backend == "container"
                else f"http://127.0.0.1:{resolved_ports[name]}"
            )
            for name in resolved_ports
        }
        env.update(
            {
                "NOVA_PLAYGROUND_PROJECT_ID": str(project["project_id"]),
                "NOVA_PLAYGROUND_SERVICE": service["name"],
                "NOVA_PLAYGROUND_KIND": service["kind"],
                "NOVA_PLAYGROUND_PORT": str(port),
                "NOVA_PLAYGROUND_WORKER_ID": worker_id,
                "NOVA_PLAYGROUND_TENANT": self.config.tenant_id,
                "NOVA_PLAYGROUND_URLS": json.dumps(service_urls, ensure_ascii=False),
                "NOVA_PLAYGROUND_PROJECT_ROOT": str(self.workspace_manager.project_root(project)),
                "NOVA_PLAYGROUND_ACTOR": session.username,
            }
        )
        if backend == "container":
            env["HOME"] = "/workspace"
            env["USERPROFILE"] = "/workspace"
            env["TMP"] = "/tmp"
            env["TEMP"] = "/tmp"
            env["TMPDIR"] = "/tmp"
            env["XDG_CACHE_HOME"] = "/workspace/.nova-cache"
        for key, value in dict(service.get("env") or {}).items():
            env[str(key)] = str(value).format_map(service_urls)
        return env

    def _service_command(
        self,
        project: dict[str, Any],
        service: dict[str, Any],
        *,
        backend: str,
        runtime_root: Path,
        env: dict[str, str],
        port: int,
        worker_id: str,
    ) -> list[str]:
        root = runtime_root
        entrypoint = root / service["entrypoint"]
        runtime = service["runtime"]
        container_port = int(service.get("port") or 0) or port
        if backend == "container":
            if self.runner is None:
                raise RuntimeError("Container-Playground benoetigt einen CodeRunner.")
            runtime_executable = shutil.which(self.runner._container_runtime({})) or self.runner._container_runtime({})
            image = self.runner._container_image(self._service_language(runtime), {})
            container_workspace = self.runner._prepare_container_workspace(runtime_root, runtime_root.parent / f".{service['name']}-container")
            base_command = self.runner._container_base_command(
                runtime_executable,
                image,
                runtime_root,
                container_workspace,
                {"web.access": False},
                network_mode_override=self._network_name(str(project["project_id"])),
                published_ports=[f"127.0.0.1:{port}:{container_port}"],
                container_name=self._container_name(worker_id),
                network_aliases=[service["name"], worker_id],
                workdir="/workspace",
                container_env=env,
            )
            if runtime == "python":
                return self.runner._container_wrapped_command(base_command, ["python", "-u", self._container_path(runtime_root, entrypoint)])
            if runtime in {"javascript", "node"}:
                return self.runner._container_wrapped_command(base_command, ["node", self._container_path(runtime_root, entrypoint)])
            if runtime == "rust":
                cargo_toml = entrypoint if entrypoint.name == "Cargo.toml" else entrypoint / "Cargo.toml"
                if cargo_toml.exists():
                    return self.runner._container_wrapped_command(base_command, ["cargo", "run", "--manifest-path", self._container_path(runtime_root, cargo_toml)])
                build_target = self._container_path(runtime_root, runtime_root / ".nova-build" / ("playground-worker.exe" if os.name == "nt" else "playground-worker"))
                source_target = self._container_path(runtime_root, entrypoint)
                return self.runner._container_wrapped_command(base_command, ["/bin/sh", "-lc", f"rustc {source_target} -o {build_target} && {build_target}"])
            raise ValueError(f"Nicht unterstuetzte Playground-Runtime fuer Container: {runtime}")
        if runtime == "python":
            executable = shutil.which("python") or shutil.which("py")
            if not executable:
                raise RuntimeError("Python ist fuer den Playground nicht verfuegbar.")
            if Path(executable).name.lower() in {"py", "py.exe"}:
                return [executable, "-3", "-u", str(entrypoint)]
            return [executable, "-u", str(entrypoint)]
        if runtime in {"javascript", "node"}:
            executable = shutil.which("node")
            if not executable:
                raise RuntimeError("Node.js ist fuer den Playground nicht verfuegbar.")
            return [executable, str(entrypoint)]
        if runtime == "rust":
            cargo_toml = entrypoint if entrypoint.name == "Cargo.toml" else entrypoint / "Cargo.toml"
            if cargo_toml.exists():
                cargo = shutil.which("cargo")
                if not cargo:
                    raise RuntimeError("Cargo ist fuer den Playground nicht verfuegbar.")
                return [cargo, "run", "--manifest-path", str(cargo_toml)]
            rustc = shutil.which("rustc")
            if not rustc:
                raise RuntimeError("rustc ist fuer den Playground nicht verfuegbar.")
            binary = entrypoint.parent / ("playground-worker.exe" if os.name == "nt" else "playground-worker")
            subprocess.run([rustc, str(entrypoint), "-o", str(binary)], check=True, capture_output=True, text=True)
            return [str(binary)]
        raise ValueError(f"Nicht unterstuetzte Playground-Runtime: {runtime}")

    def _stop_worker(self, worker: _ManagedWorker) -> None:
        if worker.backend == "container" and worker.container_name:
            runtime_name = worker.container_runtime or (self.runner._container_runtime({}) if self.runner is not None else "")
            runtime = shutil.which(runtime_name) or runtime_name
            if runtime:
                subprocess.run([runtime, "stop", worker.container_name], capture_output=True, text=True)
        if worker.process.poll() is None:
            worker.process.terminate()
            try:
                worker.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker.process.kill()
                worker.process.wait(timeout=5)

    @staticmethod
    def _find_free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _resolve_ports(self, services: list[dict[str, Any]], cluster: dict[str, _ManagedWorker]) -> dict[str, int]:
        ports: dict[str, int] = {}
        for service in services:
            if service["name"] in cluster and cluster[service["name"]].process.poll() is None:
                ports[service["name"]] = cluster[service["name"]].port
            elif int(service.get("port") or 0) > 0:
                ports[service["name"]] = int(service["port"])
            else:
                ports[service["name"]] = self._find_free_port()
        return ports

    def _log_path(self, project: dict[str, Any], service_name: str) -> Path:
        return self.workspace_manager.project_root(project) / ".nova-school" / "playground" / f"{service_name}.log"

    def _prepare_service_workspace(self, project: dict[str, Any], service_name: str) -> Path:
        runtime_root = self._service_runtime_root(project, service_name)
        if runtime_root.exists():
            shutil.rmtree(runtime_root)
        ignored_names = {"__pycache__", ".git", ".venv", "venv", "node_modules", "dist", "build", "target", ".nova-school"}

        def ignore(_directory: str, names: list[str]) -> set[str]:
            return {name for name in names if name in ignored_names}

        shutil.copytree(self.workspace_manager.project_root(project), runtime_root, ignore=ignore, dirs_exist_ok=True)
        (runtime_root / ".nova-build").mkdir(parents=True, exist_ok=True)
        return runtime_root

    def _service_runtime_root(self, project: dict[str, Any], service_name: str) -> Path:
        return self.workspace_manager.project_root(project) / ".nova-school" / "playground_runtime" / service_name

    def _ensure_network(self, project_id: str) -> None:
        if self.runner is None:
            return
        runtime = shutil.which(self.runner._container_runtime({})) or self.runner._container_runtime({})
        network_name = self._network_name(project_id)
        inspect = subprocess.run([runtime, "network", "inspect", network_name], capture_output=True, text=True)
        if inspect.returncode == 0:
            return
        create = subprocess.run([runtime, "network", "create", "--internal", network_name], capture_output=True, text=True)
        if create.returncode != 0:
            raise RuntimeError(create.stderr or f"Container-Netzwerk konnte nicht erstellt werden: {network_name}")

    def _remove_network(self, project_id: str) -> None:
        if self.runner is None:
            return
        runtime = shutil.which(self.runner._container_runtime({})) or self.runner._container_runtime({})
        subprocess.run([runtime, "network", "rm", self._network_name(project_id)], capture_output=True, text=True)

    def _resolved_backend(self, session: Any | None) -> str:
        if self.runner is None:
            return "process"
        if session is None:
            requested = self.repository.get_setting("runner_backend", "container")
            return str(requested).strip().lower() if str(requested).strip().lower() in {"process", "container"} else "container"
        return self.runner.resolve_backend(session, {}, purpose="Distributed Playground")

    def _dispatch_mode(self) -> str:
        requested = str(self.repository.get_setting("playground_dispatch_mode", "worker") or "").strip().lower()
        return requested if requested in {"worker", "local"} else "worker"

    @staticmethod
    def _container_name(worker_id: str) -> str:
        return f"nova-school-{worker_id}"

    @staticmethod
    def _network_name(project_id: str) -> str:
        return f"nova-school-playground-{project_id}"

    @staticmethod
    def _service_language(runtime: str) -> str:
        return {"python": "python", "javascript": "node", "node": "node", "rust": "rust"}.get(runtime, runtime)

    @staticmethod
    def _container_path(runtime_root: Path, target: Path) -> str:
        relative = target.resolve(strict=False).relative_to(runtime_root.resolve(strict=False)).as_posix()
        return f"/workspace/{relative}"

    @staticmethod
    def _tail_log(path: Path, max_chars: int = 2400) -> str:
        if not path.exists():
            return ""
        text = path.read_text(encoding="utf-8", errors="replace")
        return text[-max_chars:]

    @staticmethod
    def _ca_name(project_id: str) -> str:
        return f"playground-ca-{project_id}"

    @staticmethod
    def _policy_name(project_id: str) -> str:
        return f"playground-policy-{project_id}"

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import queue
import secrets
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
from urllib.parse import urlsplit
import zipfile
from pathlib import Path
from typing import Any

from .container_seccomp import resolve_seccomp_profile_option
from .worker_dispatch import RemoteWorkerDispatchService


_BLOCKED_CONTAINER_ENV_KEYS = {
    "path",
    "pathext",
    "comspec",
    "prompt",
    "systemroot",
    "windir",
    "psmodulepath",
    "appdata",
    "localappdata",
    "programdata",
    "programfiles",
    "programfiles(x86)",
    "programw6432",
    "commonprogramfiles",
    "commonprogramfiles(x86)",
    "commonprogramw6432",
    "allusersprofile",
    "onedrive",
    "public",
    "homedrive",
    "homepath",
}


class WorkerAgent:
    def __init__(
        self,
        *,
        server_url: str,
        worker_id: str,
        token: str,
        advertise_host: str,
        work_root: Path,
        heartbeat_seconds: float = 3.0,
    ) -> None:
        self.server_url = server_url.rstrip("/")
        self.worker_id = worker_id
        self.token = token
        self.advertise_host = advertise_host
        self.work_root = work_root
        self.heartbeat_seconds = max(1.0, float(heartbeat_seconds))
        self.work_root.mkdir(parents=True, exist_ok=True)

    def run_forever(self) -> None:
        while True:
            heartbeat = self._heartbeat(active_job_id="")
            if heartbeat.get("stop_job_ids"):
                time.sleep(self.heartbeat_seconds)
                continue
            claim = self._request_json("POST", "/api/worker/jobs/claim", {})
            job = claim.get("job")
            if isinstance(job, dict) and job.get("job_id"):
                self._run_job(job)
                continue
            time.sleep(self.heartbeat_seconds)

    def _run_job(self, job: dict[str, Any]) -> None:
        job_id = str(job["job_id"])
        self._verify_job(job)
        payload = dict(job.get("payload") or {})
        runtime_root = self.work_root / "jobs" / job_id / "workspace"
        artifact_path = self.work_root / "jobs" / job_id / "payload.zip"
        if runtime_root.exists():
            shutil.rmtree(runtime_root.parent, ignore_errors=True)
        runtime_root.parent.mkdir(parents=True, exist_ok=True)
        self._download(str(job["artifact_url"]), artifact_path)
        with zipfile.ZipFile(artifact_path) as archive:
            archive.extractall(runtime_root)

        env = dict(os.environ)
        env.update({str(key): str(value) for key, value in dict(payload.get("env") or {}).items()})
        command = self._build_command(job, runtime_root)
        service_url = self._service_url(payload)
        log_queue: queue.Queue[str] = queue.Queue()
        stop_requested = False

        process = subprocess.Popen(
            command,
            cwd=str(runtime_root),
            env=env if str(job.get("backend") or "") == "process" else dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )

        reader = threading.Thread(target=self._pump_stdout, args=(process, log_queue), daemon=True)
        reader.start()
        self._request_json(
            "POST",
            f"/api/worker/jobs/{job_id}/status",
            {
                "status": "running",
                "mark_started": True,
                "result": {
                    "command": command,
                    "pid": process.pid,
                    "url": service_url,
                },
            },
        )

        buffer: list[str] = []
        while process.poll() is None:
            self._drain_logs(job_id, log_queue, buffer)
            heartbeat = self._heartbeat(active_job_id=job_id)
            if job_id in list(heartbeat.get("stop_job_ids") or []):
                stop_requested = True
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            time.sleep(1.0)

        reader.join(timeout=2)
        self._drain_logs(job_id, log_queue, buffer)
        status = "stopped" if stop_requested else ("completed" if process.returncode == 0 else "failed")
        self._request_json(
            "POST",
            f"/api/worker/jobs/{job_id}/status",
            {
                "status": status,
                "mark_finished": True,
                "clear_stop_request": True,
                "result": {
                    "command": command,
                    "pid": process.pid,
                    "returncode": int(process.returncode or 0),
                    "url": service_url,
                },
            },
        )
        self._heartbeat(active_job_id="")

    @staticmethod
    def _pump_stdout(process: subprocess.Popen[str], log_queue: queue.Queue[str]) -> None:
        if process.stdout is None:
            return
        try:
            for line in process.stdout:
                log_queue.put(line)
        finally:
            process.stdout.close()

    def _drain_logs(self, job_id: str, log_queue: queue.Queue[str], buffer: list[str]) -> None:
        while True:
            try:
                buffer.append(log_queue.get_nowait())
            except queue.Empty:
                break
        if not buffer:
            return
        chunk = "".join(buffer)
        buffer.clear()
        self._request_json("POST", f"/api/worker/jobs/{job_id}/log", {"chunk": chunk})

    def _heartbeat(self, *, active_job_id: str) -> dict[str, Any]:
        return self._request_json(
            "POST",
            "/api/worker/heartbeat",
            {
                "status": "busy" if active_job_id else "active",
                "advertise_host": self.advertise_host,
                "endpoint_url": f"worker://{self.advertise_host}",
                "active_job_id": active_job_id,
            },
        )

    def _request_json(self, method: str, path: str, payload: dict[str, Any] | None) -> dict[str, Any]:
        data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = self._signed_headers(method, path, data or b"")
        headers["Content-Type"] = "application/json; charset=utf-8"
        request = urllib.request.Request(
            f"{self.server_url}{path}",
            data=data,
            method=method,
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))

    def _download(self, url: str, target: Path) -> None:
        path = urlsplit(url).path or "/"
        request = urllib.request.Request(
            url,
            method="GET",
            headers=self._signed_headers("GET", path, b""),
        )
        with urllib.request.urlopen(request, timeout=60) as response:
            target.write_bytes(response.read())

    def _verify_job(self, job: dict[str, Any]) -> None:
        signature = str(job.get("job_signature") or "")
        if not signature:
            raise RuntimeError("Dispatch-Job ist nicht signiert.")
        expected = hmac.new(
            self.token.encode("utf-8"),
            json.dumps(RemoteWorkerDispatchService._job_signature_payload(job), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise RuntimeError("Dispatch-Job-Signatur ist ungueltig.")

    def _signed_headers(self, method: str, path: str, body: bytes) -> dict[str, str]:
        timestamp = str(int(time.time()))
        nonce = secrets.token_hex(16)
        signature = RemoteWorkerDispatchService.build_worker_signature(
            secret=self.token,
            method=method,
            path=path,
            body=body,
            timestamp=timestamp,
            nonce=nonce,
        )
        return {
            "Authorization": f"Bearer {self.token}",
            "X-Nova-Worker-ID": self.worker_id,
            "X-Nova-Timestamp": timestamp,
            "X-Nova-Nonce": nonce,
            "X-Nova-Signature": signature,
        }

    def _build_command(self, job: dict[str, Any], runtime_root: Path) -> list[str]:
        payload = dict(job.get("payload") or {})
        runtime = str(payload.get("runtime") or "")
        backend = str(job.get("backend") or payload.get("backend") or "process")
        entrypoint = runtime_root / str(payload.get("entrypoint") or "")
        port = int(payload.get("port") or 0)
        env = {str(key): str(value) for key, value in dict(payload.get("env") or {}).items()}
        if backend == "container":
            runtime_executable = shutil.which(str(payload.get("container_runtime") or "docker")) or str(payload.get("container_runtime") or "docker")
            image = str(payload.get("container_image") or "")
            if not image:
                raise RuntimeError("Container-Image fehlt im Dispatch-Payload.")
            workspace_root = runtime_root.parent / "container-workspace"
            self._mirror_tree_securely(runtime_root, workspace_root, ignored_names={".nova-build", ".nova-cache", ".nova-tmp"})
            (workspace_root / ".nova-build").mkdir(parents=True, exist_ok=True)
            (workspace_root / ".nova-cache").mkdir(parents=True, exist_ok=True)
            (workspace_root / ".nova-tmp").mkdir(parents=True, exist_ok=True)
            env["HOME"] = "/workspace"
            env["USERPROFILE"] = "/workspace"
            env["TMP"] = "/tmp"
            env["TEMP"] = "/tmp"
            env["TMPDIR"] = "/tmp"
            env["XDG_CACHE_HOME"] = "/workspace/.nova-cache"
            env = {key: value for key, value in env.items() if key.strip().lower() not in _BLOCKED_CONTAINER_ENV_KEYS}
            env["PATH"] = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
            oci_runtime = str(payload.get("container_oci_runtime") or "").strip()
            command = [
                runtime_executable,
                "run",
                "--rm",
                "--init",
                "--network",
                "bridge",
                "--memory",
                str(payload.get("container_memory_limit") or "512m"),
                "--cpus",
                str(payload.get("container_cpu_limit") or "1.5"),
                "--pids-limit",
                str(payload.get("container_pids_limit") or "128"),
                "--ulimit",
                f"fsize={payload.get('container_file_size_limit_kb') or 65536}:{payload.get('container_file_size_limit_kb') or 65536}",
                "--ulimit",
                f"nofile={payload.get('container_nofile_limit') or 256}:{payload.get('container_nofile_limit') or 256}",
                "--cap-drop",
                "ALL",
                "--security-opt",
                "no-new-privileges",
                "--read-only",
                "--tmpfs",
                f"/tmp:rw,noexec,nosuid,nodev,size={payload.get('container_tmpfs_limit') or '64m'}",
                "--tmpfs",
                f"/var/tmp:rw,noexec,nosuid,nodev,size={payload.get('container_tmpfs_limit') or '64m'}",
                "-v",
                f"{workspace_root.resolve(strict=False)}:/workspace",
                "-w",
                "/workspace",
            ]
            if oci_runtime:
                command[3:3] = ["--runtime", oci_runtime]
            seccomp_opt = self._container_seccomp_option(Path(runtime_executable).name.lower())
            if seccomp_opt:
                command.extend(["--security-opt", seccomp_opt])
            for key, value in env.items():
                command.extend(["-e", f"{key}={value}"])
            if port > 0:
                command.extend(["-p", f"{port}:{port}"])
            command.append(image)
            if runtime == "python":
                return self._wrap_container_command(command, ["python", "-u", f"/workspace/{entrypoint.relative_to(runtime_root).as_posix()}"])
            if runtime in {"javascript", "node"}:
                return self._wrap_container_command(command, ["node", f"/workspace/{entrypoint.relative_to(runtime_root).as_posix()}"])
            if runtime == "rust":
                cargo_toml = entrypoint if entrypoint.name == "Cargo.toml" else entrypoint / "Cargo.toml"
                if cargo_toml.exists():
                    return self._wrap_container_command(command, ["cargo", "run", "--manifest-path", f"/workspace/{cargo_toml.relative_to(runtime_root).as_posix()}"])
                binary = "/workspace/.nova-build/playground-worker"
                source = f"/workspace/{entrypoint.relative_to(runtime_root).as_posix()}"
                return self._wrap_container_command(command, ["/bin/sh", "-lc", f"rustc {source} -o {binary} && {binary}"])
            raise ValueError(f"Nicht unterstuetzte Playground-Runtime fuer Container: {runtime}")
        if runtime == "python":
            executable = shutil.which("python") or shutil.which("py")
            if not executable:
                raise RuntimeError("Python ist auf dem Worker nicht verfuegbar.")
            if Path(executable).name.lower() in {"py", "py.exe"}:
                return [executable, "-3", "-u", str(entrypoint)]
            return [executable, "-u", str(entrypoint)]
        if runtime in {"javascript", "node"}:
            executable = shutil.which("node")
            if not executable:
                raise RuntimeError("Node.js ist auf dem Worker nicht verfuegbar.")
            return [executable, str(entrypoint)]
        if runtime == "rust":
            cargo_toml = entrypoint if entrypoint.name == "Cargo.toml" else entrypoint / "Cargo.toml"
            if cargo_toml.exists():
                cargo = shutil.which("cargo")
                if not cargo:
                    raise RuntimeError("Cargo ist auf dem Worker nicht verfuegbar.")
                return [cargo, "run", "--manifest-path", str(cargo_toml)]
            rustc = shutil.which("rustc")
            if not rustc:
                raise RuntimeError("rustc ist auf dem Worker nicht verfuegbar.")
            build_dir = runtime_root / ".nova-build"
            build_dir.mkdir(parents=True, exist_ok=True)
            binary = build_dir / ("playground-worker.exe" if os.name == "nt" else "playground-worker")
            subprocess.run([rustc, str(entrypoint), "-o", str(binary)], check=True, capture_output=True, text=True)
            return [str(binary)]
        raise ValueError(f"Nicht unterstuetzte Playground-Runtime: {runtime}")

    def _service_url(self, payload: dict[str, Any]) -> str:
        port = int(payload.get("port") or 0)
        return f"http://{self.advertise_host}:{port}" if port > 0 else ""

    @staticmethod
    def _wrap_container_command(base_command: list[str], inner_command: list[str]) -> list[str]:
        return [*base_command, *inner_command]

    def _mirror_tree_securely(self, source_root: Path, target_root: Path, *, ignored_names: set[str]) -> None:
        if target_root.exists():
            shutil.rmtree(target_root, ignore_errors=True)
        target_root.mkdir(parents=True, exist_ok=True)
        self._copy_tree_entries_securely(source_root, target_root, ignored_names)

    def _copy_tree_entries_securely(self, source_dir: Path, target_dir: Path, ignored_names: set[str]) -> None:
        with os.scandir(source_dir) as entries:
            for entry in entries:
                if entry.name in ignored_names:
                    continue
                source_path = Path(entry.path)
                target_path = target_dir / entry.name
                if self._is_link_like(source_path):
                    raise RuntimeError(f"Symbolische Links oder Junctions sind im Worker-Dispatch-Workspace nicht erlaubt: {source_path}")
                if entry.is_dir(follow_symlinks=False):
                    target_path.mkdir(parents=True, exist_ok=True)
                    self._copy_tree_entries_securely(source_path, target_path, ignored_names)
                    continue
                if entry.is_file(follow_symlinks=False):
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_path, target_path)
                    continue
                raise RuntimeError(f"Nicht unterstuetzter Dateityp im Worker-Dispatch-Workspace: {source_path}")

    @staticmethod
    def _is_link_like(path: Path) -> bool:
        if path.is_symlink():
            return True
        is_junction = getattr(path, "is_junction", None)
        if callable(is_junction):
            try:
                return bool(is_junction())
            except OSError:
                return True
        return False

    @staticmethod
    def _container_seccomp_option(runtime_name: str) -> str | None:
        profile_path = Path(__file__).resolve().parent / "seccomp_profiles" / "container-denylist.json"
        if not profile_path.exists():
            return None
        return resolve_seccomp_profile_option(profile_path, runtime_name)


def _default_advertise_host() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            ip = probe.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except OSError:
        pass
    return socket.gethostname()


def main() -> None:
    parser = argparse.ArgumentParser(description="Nova School Remote Worker Agent")
    parser.add_argument("--server", required=True, help="Nova School Server Basis-URL, z.B. http://192.168.178.62:8877")
    parser.add_argument("--worker-id", required=True, help="Eindeutige Worker-ID")
    parser.add_argument("--token", required=True, help="Bootstrap-Token aus dem Server")
    parser.add_argument("--advertise-host", default=_default_advertise_host(), help="Host/IP, unter der andere Worker diesen Node erreichen")
    parser.add_argument("--work-root", default=str(Path.home() / ".nova-school-worker"), help="Lokales Arbeitsverzeichnis des Workers")
    parser.add_argument("--heartbeat-seconds", type=float, default=3.0, help="Heartbeat-Intervall in Sekunden")
    args = parser.parse_args()

    agent = WorkerAgent(
        server_url=str(args.server),
        worker_id=str(args.worker_id),
        token=str(args.token),
        advertise_host=str(args.advertise_host),
        work_root=Path(str(args.work_root)).resolve(strict=False),
        heartbeat_seconds=float(args.heartbeat_seconds),
    )
    agent.run_forever()


if __name__ == "__main__":
    main()

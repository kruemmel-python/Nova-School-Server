from __future__ import annotations

import base64
import codecs
import hashlib
import json
import socket
import struct
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Callable

from .auth import SessionContext
from .code_runner import CodeRunner, LivePreparedRun
from .database import SchoolRepository
from .pty_host import PtyProcess, create_pty_process, normalize_terminal_size


WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class WebSocketConnection:
    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.sock.settimeout(None)
        self._send_lock = threading.Lock()
        self._closed = threading.Event()

    def send_json(self, payload: dict[str, Any]) -> None:
        self.send_text(json.dumps(payload, ensure_ascii=False))

    def send_text(self, text: str) -> None:
        self._send_frame(0x1, text.encode("utf-8"))

    def recv_json(self) -> dict[str, Any]:
        payload = self.recv_text()
        return dict(json.loads(payload))

    def recv_text(self) -> str:
        while True:
            opcode, payload = self._recv_frame()
            if opcode == 0x1:
                return payload.decode("utf-8")
            if opcode == 0x8:
                self.close()
                raise ConnectionError("WebSocket wurde geschlossen.")
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0xA:
                continue
            raise ConnectionError(f"Nicht unterstuetzter WebSocket-Opcode: {opcode}")

    def close(self, code: int = 1000, reason: str = "") -> None:
        if self._closed.is_set():
            return
        self._closed.set()
        payload = struct.pack("!H", code) + reason.encode("utf-8")
        try:
            self._send_frame(0x8, payload)
        except Exception:
            pass
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        try:
            self.sock.close()
        except Exception:
            pass

    @staticmethod
    def accept_key(key: str) -> str:
        digest = hashlib.sha1((key + WS_MAGIC).encode("ascii")).digest()
        return base64.b64encode(digest).decode("ascii")

    def _recv_frame(self) -> tuple[int, bytes]:
        header = self._recv_exact(2)
        first, second = header[0], header[1]
        opcode = first & 0x0F
        masked = bool(second & 0x80)
        payload_len = second & 0x7F
        if payload_len == 126:
            payload_len = struct.unpack("!H", self._recv_exact(2))[0]
        elif payload_len == 127:
            payload_len = struct.unpack("!Q", self._recv_exact(8))[0]
        mask = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(payload_len) if payload_len else b""
        if masked:
            payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
        return opcode, payload

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        if self._closed.is_set():
            return
        length = len(payload)
        if length < 126:
            header = bytes([0x80 | opcode, length])
        elif length < 65536:
            header = bytes([0x80 | opcode, 126]) + struct.pack("!H", length)
        else:
            header = bytes([0x80 | opcode, 127]) + struct.pack("!Q", length)
        with self._send_lock:
            self.sock.sendall(header + payload)

    def _recv_exact(self, size: int) -> bytes:
        chunks = bytearray()
        while len(chunks) < size:
            try:
                chunk = self.sock.recv(size - len(chunks))
            except (TimeoutError, socket.timeout) as exc:
                raise ConnectionError("WebSocket-Zeitlimit erreicht.") from exc
            if not chunk:
                raise ConnectionError("WebSocket-Verbindung beendet.")
            chunks.extend(chunk)
        return bytes(chunks)


@dataclass(slots=True)
class RealtimeClient:
    client_id: str
    connection: WebSocketConnection
    session: SessionContext
    project: dict[str, Any]


@dataclass(slots=True)
class ActiveLiveRun:
    session_id: str
    run_id: str
    client_id: str
    owner_username: str
    project_id: str
    project_name: str
    language: str
    command: list[str]
    notes: list[str]
    tool_session: dict[str, Any]
    process: subprocess.Popen[str] | None
    pty_process: PtyProcess | None
    started_at: float
    emit: Callable[[dict[str, Any]], None]
    client_meta: dict[str, Any]
    preview_path: str = ""
    timed_out: bool = False
    terminal: dict[str, Any] | None = None
    decoder: Any | None = None
    scheduler_lease: Any | None = None


class LiveRunManager:
    def __init__(self, runner: CodeRunner, repository: SchoolRepository) -> None:
        self.runner = runner
        self.repository = repository
        self._lock = threading.RLock()
        self._sessions: dict[str, ActiveLiveRun] = {}

    def close(self) -> None:
        with self._lock:
            session_ids = list(self._sessions)
        for session_id in session_ids:
            self._terminate(session_id, force=True)

    def stop_for_client(self, client_id: str) -> None:
        with self._lock:
            session_ids = [session_id for session_id, handle in self._sessions.items() if handle.client_id == client_id]
        for session_id in session_ids:
            self._terminate(session_id, force=True)

    def start(self, client: RealtimeClient, payload: dict[str, Any]) -> None:
        prepared = self.runner.prepare_live_run(client.session, client.project, payload)
        client_meta = dict(payload.get("client_meta") or {})
        terminal = self._terminal_payload(payload)
        notes = list(prepared.notes)
        if prepared.failed_returncode is not None:
            client.connection.send_json(
                {
                    "type": "run.started",
                    "session_id": prepared.session_id,
                    "run_id": prepared.run_id,
                    "language": prepared.language,
                    "command": prepared.command,
                    "notes": notes,
                    "tool_session": prepared.tool_session,
                    "preview_path": prepared.preview_path,
                    "client_meta": client_meta,
                    "terminal": terminal,
                }
            )
            if prepared.prelude_stdout:
                client.connection.send_json({"type": "run.output", "session_id": prepared.session_id, "stream": "stdout", "chunk": prepared.prelude_stdout, "client_meta": client_meta})
            if prepared.prelude_stderr:
                client.connection.send_json({"type": "run.output", "session_id": prepared.session_id, "stream": "stderr", "chunk": prepared.prelude_stderr, "client_meta": client_meta})
            self._emit_exit(
                prepared,
                client.session.username,
                prepared.failed_returncode,
                duration_ms=0,
                timed_out=False,
                emitter=client.connection.send_json,
                client_meta=client_meta,
                terminal=terminal,
                notes=notes,
            )
            self.runner.scheduler.release(prepared.scheduler_lease)
            return

        process: subprocess.Popen[str] | None = None
        pty_process: PtyProcess | None = None
        try:
            if terminal["requested"]:
                try:
                    pty_command = prepared.pty_command or prepared.command
                    pty_process = create_pty_process(pty_command, prepared.cwd, prepared.env, terminal["cols"], terminal["rows"])
                    terminal["pty"] = True
                    terminal["mode"] = "pty"
                    notes.append("Native PTY-/ConPTY-Terminalsitzung aktiv.")
                except Exception as exc:
                    terminal["pty"] = False
                    terminal["mode"] = "pipe"
                    notes.append(f"PTY nicht verfuegbar, Pipe-Modus aktiv: {exc}")
            if pty_process is None:
                process = subprocess.Popen(
                    prepared.command,
                    cwd=str(prepared.cwd),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    env=prepared.env,
                    bufsize=0,
                    shell=False,
                )
            handle = ActiveLiveRun(
                session_id=prepared.session_id,
                run_id=prepared.run_id,
                client_id=client.client_id,
                owner_username=client.session.username,
                project_id=str(client.project["project_id"]),
                project_name=str(client.project["name"]),
                language=prepared.language,
                command=(prepared.pty_command or prepared.command) if pty_process is not None else prepared.command,
                notes=notes,
                tool_session=prepared.tool_session,
                process=process,
                pty_process=pty_process,
                started_at=time.perf_counter(),
                emit=client.connection.send_json,
                client_meta=client_meta,
                preview_path=prepared.preview_path,
                terminal=terminal,
                decoder=codecs.getincrementaldecoder("utf-8")("replace") if pty_process is not None else None,
                scheduler_lease=prepared.scheduler_lease,
            )
        except Exception:
            self.runner.scheduler.release(prepared.scheduler_lease)
            raise
        with self._lock:
            self._sessions[handle.session_id] = handle
        client.connection.send_json(
            {
                "type": "run.started",
                "session_id": prepared.session_id,
                "run_id": prepared.run_id,
                "language": prepared.language,
                "command": handle.command,
                "notes": handle.notes,
                "tool_session": prepared.tool_session,
                "preview_path": prepared.preview_path,
                "client_meta": client_meta,
                "terminal": terminal,
            }
        )
        if prepared.prelude_stdout:
            client.connection.send_json({"type": "run.output", "session_id": prepared.session_id, "stream": "stdout", "chunk": prepared.prelude_stdout, "client_meta": client_meta})
        if prepared.prelude_stderr:
            client.connection.send_json({"type": "run.output", "session_id": prepared.session_id, "stream": "stderr", "chunk": prepared.prelude_stderr, "client_meta": client_meta})
        if pty_process is not None:
            threading.Thread(target=self._pump_terminal, args=(handle.session_id,), daemon=True).start()
        elif process is not None:
            for stream_name, stream in (("stdout", process.stdout), ("stderr", process.stderr)):
                if stream is None:
                    continue
                threading.Thread(target=self._pump_stream, args=(handle.session_id, stream_name, stream), daemon=True).start()
        threading.Thread(target=self._watch_process, args=(handle.session_id,), daemon=True).start()

    def send_input(self, actor: SessionContext, session_id: str, text: str) -> None:
        handle = self._session(session_id)
        self._ensure_control(actor, handle)
        if handle.pty_process is not None:
            if handle.pty_process.poll() is not None:
                raise ValueError("Live-Session ist nicht mehr aktiv.")
            handle.pty_process.write(str(text).encode("utf-8"))
            return
        if handle.process is None or handle.process.poll() is not None or handle.process.stdin is None:
            raise ValueError("Live-Session ist nicht mehr aktiv.")
        handle.process.stdin.write(text)
        handle.process.stdin.flush()

    def resize(self, actor: SessionContext, session_id: str, cols: int, rows: int) -> None:
        handle = self._session(session_id)
        self._ensure_control(actor, handle)
        if handle.pty_process is None:
            return
        width, height = normalize_terminal_size(cols, rows)
        handle.pty_process.resize(width, height)
        terminal = dict(handle.terminal or {})
        terminal.update({"requested": True, "pty": True, "mode": "pty", "cols": width, "rows": height})
        handle.terminal = terminal

    def stop(self, actor: SessionContext, session_id: str) -> None:
        handle = self._session(session_id)
        self._ensure_control(actor, handle)
        self._terminate(session_id, force=False)

    def _pump_stream(self, session_id: str, stream_name: str, stream: Any) -> None:
        buffer: list[str] = []
        try:
            while True:
                chunk = stream.read(1)
                if chunk == "":
                    break
                buffer.append(chunk)
                if chunk == "\n" or len(buffer) >= 64:
                    self._emit_chunk(session_id, stream_name, "".join(buffer))
                    buffer = []
            if buffer:
                self._emit_chunk(session_id, stream_name, "".join(buffer))
        finally:
            try:
                stream.close()
            except Exception:
                pass

    def _pump_terminal(self, session_id: str) -> None:
        try:
            handle = self._session(session_id)
        except FileNotFoundError:
            return
        if handle.pty_process is None:
            return
        decoder = handle.decoder or codecs.getincrementaldecoder("utf-8")("replace")
        try:
            while True:
                chunk = handle.pty_process.read(4096)
                if not chunk:
                    if handle.pty_process.poll() is None:
                        time.sleep(0.02)
                        continue
                    break
                text = decoder.decode(chunk)
                if text:
                    self._emit_chunk(session_id, "stdout", text)
            tail = decoder.decode(b"", final=True)
            if tail:
                self._emit_chunk(session_id, "stdout", tail)
        finally:
            handle.decoder = None

    def _watch_process(self, session_id: str) -> None:
        handle = self._session(session_id)
        deadline = time.perf_counter() + self.runner.config.live_run_timeout_seconds
        while self._poll_handle(handle) is None:
            if time.perf_counter() >= deadline:
                handle.timed_out = True
                self._terminate(session_id, force=True)
                break
            time.sleep(0.1)
        if handle.pty_process is not None:
            time.sleep(0.1)
        returncode = self._wait_handle(handle)
        if handle.pty_process is not None:
            handle.pty_process.close()
        duration_ms = int((time.perf_counter() - handle.started_at) * 1000)
        self._emit_exit_from_handle(handle, returncode, duration_ms)
        time.sleep(0.1)
        with self._lock:
            self._sessions.pop(session_id, None)

    def _emit_chunk(self, session_id: str, stream_name: str, chunk: str) -> None:
        try:
            handle = self._session(session_id)
        except FileNotFoundError:
            return
        handle.emit({"type": "run.output", "session_id": session_id, "stream": stream_name, "chunk": chunk, "client_meta": handle.client_meta})

    def _emit_exit_from_handle(self, handle: ActiveLiveRun, returncode: int, duration_ms: int) -> None:
        payload = {
            "type": "run.exit",
            "session_id": handle.session_id,
            "run_id": handle.run_id,
            "language": handle.language,
            "returncode": returncode,
            "duration_ms": duration_ms,
            "timed_out": handle.timed_out,
            "notes": handle.notes + (["Zeitlimit erreicht."] if handle.timed_out else []),
            "preview_path": handle.preview_path,
            "command": handle.command,
            "client_meta": handle.client_meta,
            "terminal": handle.terminal or {},
        }
        handle.emit(payload)
        try:
            self.repository.add_audit(
                handle.owner_username,
                "project.run.live",
                "project",
                handle.project_id,
                {
                    "project_name": handle.project_name,
                    "language": handle.language,
                    "returncode": returncode,
                    "duration_ms": duration_ms,
                    "timed_out": handle.timed_out,
                    "command": handle.command,
                    "preview_path": handle.preview_path,
                },
            )
        except Exception:
            pass
        finally:
            self.runner.scheduler.release(handle.scheduler_lease)

    def _emit_exit(self, prepared: LivePreparedRun, actor_username: str, returncode: int, duration_ms: int, timed_out: bool, emitter: Callable[[dict[str, Any]], None], client_meta: dict[str, Any], terminal: dict[str, Any] | None = None, notes: list[str] | None = None) -> None:
        emitter(
            {
                "type": "run.exit",
                "session_id": prepared.session_id,
                "run_id": prepared.run_id,
                "language": prepared.language,
                "returncode": returncode,
                "duration_ms": duration_ms,
                "timed_out": timed_out,
                "notes": (notes if notes is not None else prepared.notes) + (["Zeitlimit erreicht."] if timed_out else []),
                "preview_path": prepared.preview_path,
                "command": prepared.command,
                "client_meta": client_meta,
                "terminal": terminal or {},
            }
        )
        try:
            self.repository.add_audit(
                actor_username,
                "project.run.live",
                "project",
                str(prepared.run_id),
                {
                    "language": prepared.language,
                    "returncode": returncode,
                    "duration_ms": duration_ms,
                    "timed_out": timed_out,
                    "command": prepared.command,
                    "preview_path": prepared.preview_path,
                },
            )
        except Exception:
            pass
        finally:
            self.runner.scheduler.release(prepared.scheduler_lease)

    def _session(self, session_id: str) -> ActiveLiveRun:
        with self._lock:
            handle = self._sessions.get(session_id)
        if handle is None:
            raise FileNotFoundError("Live-Session nicht gefunden.")
        return handle

    @staticmethod
    def _ensure_control(actor: SessionContext, handle: ActiveLiveRun) -> None:
        if actor.username != handle.owner_username and not actor.is_teacher:
            raise PermissionError("Nur Besitzer oder Lehrkraefte duerfen diese Live-Session steuern.")

    def _terminate(self, session_id: str, *, force: bool) -> None:
        handle = self._session(session_id)
        if handle.pty_process is not None:
            if handle.pty_process.poll() is not None:
                return
            handle.pty_process.terminate(force=force)
            return
        if handle.process is None or handle.process.poll() is not None:
            return
        handle.process.terminate()
        try:
            handle.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            if force:
                handle.process.kill()
                handle.process.wait(timeout=2)

    @staticmethod
    def _terminal_payload(payload: dict[str, Any]) -> dict[str, Any]:
        terminal = payload.get("terminal") if isinstance(payload.get("terminal"), dict) else {}
        requested = bool(terminal.get("pty"))
        cols, rows = normalize_terminal_size(terminal.get("cols"), terminal.get("rows"))
        return {
            "requested": requested,
            "pty": False,
            "mode": "pipe",
            "cols": cols,
            "rows": rows,
        }

    @staticmethod
    def _poll_handle(handle: ActiveLiveRun) -> int | None:
        if handle.pty_process is not None:
            return handle.pty_process.poll()
        if handle.process is None:
            return 0
        return handle.process.poll()

    @staticmethod
    def _wait_handle(handle: ActiveLiveRun) -> int:
        if handle.pty_process is not None:
            return handle.pty_process.wait()
        if handle.process is None:
            return 0
        return handle.process.wait()


class RealtimeService:
    def __init__(self, application: Any) -> None:
        self.application = application
        self.live_runs = LiveRunManager(application.runner, application.repository)
        self._lock = threading.RLock()
        self._project_clients: dict[str, dict[str, RealtimeClient]] = {}

    def close(self) -> None:
        self.live_runs.close()
        with self._lock:
            clients = [client for per_project in self._project_clients.values() for client in per_project.values()]
            self._project_clients.clear()
        for client in clients:
            client.connection.close()

    def handle_project_socket(self, connection: WebSocketConnection, session: SessionContext, project: dict[str, Any]) -> None:
        client = RealtimeClient(uuid.uuid4().hex[:12], connection, session, project)
        self._register(client)
        try:
            connection.send_json({"type": "hello", "project_id": project["project_id"], "username": session.username})
            if session.permissions.get("notebook.collaborate", False):
                snapshot = self.application.collaboration.snapshot(project)
                connection.send_json({"type": "collab.state", **snapshot})
            while True:
                message = connection.recv_json()
                try:
                    self._handle_message(client, message)
                except Exception as exc:
                    try:
                        connection.send_json({"type": "error", "message": str(exc)})
                    except Exception:
                        break
        except (ConnectionError, TimeoutError, OSError):
            pass
        finally:
            self.live_runs.stop_for_client(client.client_id)
            self._unregister(client)
            connection.close()

    def _handle_message(self, client: RealtimeClient, message: dict[str, Any]) -> None:
        action = str(message.get("action") or "").strip().lower()
        if action == "ping":
            client.connection.send_json({"type": "pong", "ts": time.time()})
            return
        if action == "collab.presence":
            self._require_permission(client.session, "notebook.collaborate")
            presence = self.application.collaboration.heartbeat(
                client.session,
                client.project,
                cursor=message.get("cursor") if isinstance(message.get("cursor"), dict) else None,
            )
            self._broadcast_project(str(client.project["project_id"]), {"type": "collab.presence", "presence": presence})
            return
        if action == "collab.sync":
            self._require_permission(client.session, "notebook.collaborate")
            payload = self.application.collaboration.sync(
                client.session,
                client.project,
                list(message.get("cells") or []),
                int(message.get("base_revision") or 0),
                cursor=message.get("cursor") if isinstance(message.get("cursor"), dict) else None,
            )
            self._broadcast_project(str(client.project["project_id"]), {"type": "collab.state", **payload, "actor": client.session.username})
            return
        if action == "run.start":
            self.live_runs.start(client, dict(message.get("payload") or {}))
            return
        if action == "run.stdin":
            session_id = str(message.get("session_id") or "").strip()
            if not session_id:
                raise ValueError("session_id fuer Live-Eingabe fehlt.")
            self.live_runs.send_input(client.session, session_id, str(message.get("text") or ""))
            return
        if action == "run.resize":
            session_id = str(message.get("session_id") or "").strip()
            if not session_id:
                raise ValueError("session_id fuer Resize fehlt.")
            terminal = message.get("terminal") if isinstance(message.get("terminal"), dict) else {}
            self.live_runs.resize(client.session, session_id, int(terminal.get("cols") or 120), int(terminal.get("rows") or 30))
            return
        if action == "run.stop":
            session_id = str(message.get("session_id") or "").strip()
            if not session_id:
                raise ValueError("session_id fuer Stop fehlt.")
            self.live_runs.stop(client.session, session_id)
            return
        raise ValueError(f"Unbekannte Echtzeit-Aktion: {action or 'leer'}")

    def _broadcast_project(self, project_id: str, payload: dict[str, Any]) -> None:
        with self._lock:
            clients = list(self._project_clients.get(project_id, {}).values())
        for client in clients:
            try:
                client.connection.send_json(payload)
            except Exception:
                self._unregister(client)

    def _register(self, client: RealtimeClient) -> None:
        with self._lock:
            self._project_clients.setdefault(str(client.project["project_id"]), {})[client.client_id] = client

    def _unregister(self, client: RealtimeClient) -> None:
        project_id = str(client.project["project_id"])
        with self._lock:
            bucket = self._project_clients.get(project_id, {})
            bucket.pop(client.client_id, None)
            if not bucket and project_id in self._project_clients:
                self._project_clients.pop(project_id, None)

    @staticmethod
    def _require_permission(session: SessionContext, key: str) -> None:
        if not session.permissions.get(key, False):
            raise PermissionError(f"Recht fehlt: {key}")


def upgrade_websocket(handler: Any) -> WebSocketConnection:
    upgrade = str(handler.headers.get("Upgrade", "")).strip().lower()
    if upgrade != "websocket":
        raise ValueError("WebSocket-Upgrade erwartet.")
    key = str(handler.headers.get("Sec-WebSocket-Key", "")).strip()
    if not key:
        raise ValueError("Sec-WebSocket-Key fehlt.")
    handler.send_response(HTTPStatus.SWITCHING_PROTOCOLS)
    handler.send_header("Upgrade", "websocket")
    handler.send_header("Connection", "Upgrade")
    handler.send_header("Sec-WebSocket-Accept", WebSocketConnection.accept_key(key))
    handler.end_headers()
    handler.close_connection = True
    setattr(handler, "_websocket_upgraded", True)
    return WebSocketConnection(handler.connection)

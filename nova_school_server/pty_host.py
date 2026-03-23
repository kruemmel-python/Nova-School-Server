from __future__ import annotations

import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Sequence


def normalize_terminal_size(cols: int | None, rows: int | None) -> tuple[int, int]:
    width = max(40, min(320, int(cols or 120)))
    height = max(10, min(120, int(rows or 30)))
    return width, height


class PtyProcess:
    def read(self, size: int = 4096) -> bytes:
        raise NotImplementedError

    def write(self, data: bytes) -> int:
        raise NotImplementedError

    def resize(self, cols: int, rows: int) -> None:
        raise NotImplementedError

    def poll(self) -> int | None:
        raise NotImplementedError

    def wait(self, timeout: float | None = None) -> int:
        raise NotImplementedError

    def terminate(self, force: bool = False) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


if os.name == "nt":
    import ctypes
    from ctypes import wintypes

    try:
        from winpty import Backend as WinptyBackend
        from winpty import PtyProcess as WinptyProcess
    except Exception:  # pragma: no cover - optional dependency
        WinptyBackend = None
        WinptyProcess = None

    HRESULT = ctypes.c_long
    SIZE_T = ctypes.c_size_t
    DWORD_PTR = ctypes.c_size_t

    PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE = 0x00020016
    EXTENDED_STARTUPINFO_PRESENT = 0x00080000
    CREATE_UNICODE_ENVIRONMENT = 0x00000400
    WAIT_OBJECT_0 = 0
    WAIT_TIMEOUT = 258
    STILL_ACTIVE = 259
    HANDLE_FLAG_INHERIT = 0x00000001

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    class COORD(ctypes.Structure):
        _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]

    class STARTUPINFOW(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("lpReserved", wintypes.LPWSTR),
            ("lpDesktop", wintypes.LPWSTR),
            ("lpTitle", wintypes.LPWSTR),
            ("dwX", wintypes.DWORD),
            ("dwY", wintypes.DWORD),
            ("dwXSize", wintypes.DWORD),
            ("dwYSize", wintypes.DWORD),
            ("dwXCountChars", wintypes.DWORD),
            ("dwYCountChars", wintypes.DWORD),
            ("dwFillAttribute", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("wShowWindow", wintypes.WORD),
            ("cbReserved2", wintypes.WORD),
            ("lpReserved2", ctypes.POINTER(ctypes.c_ubyte)),
            ("hStdInput", wintypes.HANDLE),
            ("hStdOutput", wintypes.HANDLE),
            ("hStdError", wintypes.HANDLE),
        ]

    class STARTUPINFOEXW(ctypes.Structure):
        _fields_ = [("StartupInfo", STARTUPINFOW), ("lpAttributeList", ctypes.c_void_p)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("hProcess", wintypes.HANDLE),
            ("hThread", wintypes.HANDLE),
            ("dwProcessId", wintypes.DWORD),
            ("dwThreadId", wintypes.DWORD),
        ]

    CreatePipe = kernel32.CreatePipe
    CreatePipe.argtypes = [ctypes.POINTER(wintypes.HANDLE), ctypes.POINTER(wintypes.HANDLE), ctypes.c_void_p, wintypes.DWORD]
    CreatePipe.restype = wintypes.BOOL

    CloseHandle = kernel32.CloseHandle
    CloseHandle.argtypes = [wintypes.HANDLE]
    CloseHandle.restype = wintypes.BOOL

    SetHandleInformation = kernel32.SetHandleInformation
    SetHandleInformation.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD]
    SetHandleInformation.restype = wintypes.BOOL

    WaitForSingleObject = kernel32.WaitForSingleObject
    WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    WaitForSingleObject.restype = wintypes.DWORD

    GetExitCodeProcess = kernel32.GetExitCodeProcess
    GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    GetExitCodeProcess.restype = wintypes.BOOL

    TerminateProcess = kernel32.TerminateProcess
    TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
    TerminateProcess.restype = wintypes.BOOL

    ReadFile = kernel32.ReadFile
    ReadFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    ReadFile.restype = wintypes.BOOL

    WriteFile = kernel32.WriteFile
    WriteFile.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p]
    WriteFile.restype = wintypes.BOOL

    InitializeProcThreadAttributeList = kernel32.InitializeProcThreadAttributeList
    InitializeProcThreadAttributeList.argtypes = [ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(SIZE_T)]
    InitializeProcThreadAttributeList.restype = wintypes.BOOL

    UpdateProcThreadAttribute = kernel32.UpdateProcThreadAttribute
    UpdateProcThreadAttribute.argtypes = [ctypes.c_void_p, wintypes.DWORD, DWORD_PTR, ctypes.c_void_p, SIZE_T, ctypes.c_void_p, ctypes.POINTER(SIZE_T)]
    UpdateProcThreadAttribute.restype = wintypes.BOOL

    DeleteProcThreadAttributeList = kernel32.DeleteProcThreadAttributeList
    DeleteProcThreadAttributeList.argtypes = [ctypes.c_void_p]
    DeleteProcThreadAttributeList.restype = None

    CreateProcessW = kernel32.CreateProcessW
    CreateProcessW.argtypes = [
        wintypes.LPCWSTR,
        wintypes.LPWSTR,
        ctypes.c_void_p,
        ctypes.c_void_p,
        wintypes.BOOL,
        wintypes.DWORD,
        ctypes.c_void_p,
        wintypes.LPCWSTR,
        ctypes.c_void_p,
        ctypes.POINTER(PROCESS_INFORMATION),
    ]
    CreateProcessW.restype = wintypes.BOOL

    CreatePseudoConsole = getattr(kernel32, "CreatePseudoConsole", None)
    ResizePseudoConsole = getattr(kernel32, "ResizePseudoConsole", None)
    ClosePseudoConsole = getattr(kernel32, "ClosePseudoConsole", None)
    if CreatePseudoConsole is not None:
        CreatePseudoConsole.argtypes = [COORD, wintypes.HANDLE, wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
        CreatePseudoConsole.restype = HRESULT
    if ResizePseudoConsole is not None:
        ResizePseudoConsole.argtypes = [wintypes.HANDLE, COORD]
        ResizePseudoConsole.restype = HRESULT
    if ClosePseudoConsole is not None:
        ClosePseudoConsole.argtypes = [wintypes.HANDLE]
        ClosePseudoConsole.restype = None

    def _raise_last_error(message: str) -> None:
        error = ctypes.get_last_error()
        raise OSError(f"{message}: {ctypes.WinError(error)}")

    def _raise_hresult(message: str, code: int) -> None:
        raise OSError(f"{message} (HRESULT 0x{code & 0xFFFFFFFF:08X})")

    def _close_handle(handle: wintypes.HANDLE | None) -> None:
        if handle is None:
            return
        value = getattr(handle, "value", None)
        if value:
            CloseHandle(handle)

    def _set_no_inherit(handle: wintypes.HANDLE) -> None:
        if not SetHandleInformation(handle, HANDLE_FLAG_INHERIT, 0):
            _raise_last_error("Handle-Attribute konnten nicht gesetzt werden")

    def _create_pipe() -> tuple[wintypes.HANDLE, wintypes.HANDLE]:
        read_handle = wintypes.HANDLE()
        write_handle = wintypes.HANDLE()
        if not CreatePipe(ctypes.byref(read_handle), ctypes.byref(write_handle), None, 0):
            _raise_last_error("Anonyme Pipe konnte nicht erstellt werden")
        return read_handle, write_handle

    def _build_environment_block(env: dict[str, str] | None) -> ctypes.Array[ctypes.c_wchar] | None:
        if env is None:
            return None
        payload = "\0".join(f"{key}={value}" for key, value in sorted(env.items(), key=lambda item: item[0].upper())) + "\0\0"
        return ctypes.create_unicode_buffer(payload)

    def _build_attribute_list(hpc: wintypes.HANDLE) -> tuple[ctypes.Array[ctypes.c_char], ctypes.c_void_p]:
        size = SIZE_T()
        InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not InitializeProcThreadAttributeList(buffer, 1, 0, ctypes.byref(size)):
            _raise_last_error("Attributliste fuer ConPTY konnte nicht initialisiert werden")
        attr_list = ctypes.cast(buffer, ctypes.c_void_p)
        if not UpdateProcThreadAttribute(
            attr_list,
            0,
            PROC_THREAD_ATTRIBUTE_PSEUDOCONSOLE,
            ctypes.byref(hpc),
            SIZE_T(ctypes.sizeof(wintypes.HANDLE)),
            None,
            None,
        ):
            DeleteProcThreadAttributeList(attr_list)
            _raise_last_error("ConPTY-Attribut konnte nicht gesetzt werden")
        return buffer, attr_list

    def _normalize_windows_input(data: bytes) -> str:
        text = data.decode("utf-8", "replace")
        text = text.replace("\r\n", "\r").replace("\n", "\r")
        return text

    class _PyWinPtyProcess(PtyProcess):
        def __init__(self, command: Sequence[str], cwd: Path, env: dict[str, str], cols: int, rows: int) -> None:
            if WinptyProcess is None:
                raise OSError("pywinpty ist nicht verfuegbar.")
            self.command = [str(part) for part in command]
            self.cwd = Path(cwd)
            self.cols, self.rows = normalize_terminal_size(cols, rows)
            self.pid = 0
            self._closed = False
            self._output_buffer = bytearray()
            self._output_closed = False
            self._output_lock = threading.Lock()
            self._output_ready = threading.Condition(self._output_lock)
            backend = getattr(WinptyBackend, "ConPTY", None) if WinptyBackend is not None else None
            self.process = WinptyProcess.spawn(self.command, cwd=str(self.cwd), env=env, dimensions=(self.rows, self.cols), backend=backend)
            self.pid = int(getattr(self.process, "pid", 0) or 0)
            threading.Thread(target=self._capture_output, daemon=True).start()

        def _capture_output(self) -> None:
            try:
                while True:
                    chunk = self.process.read(4096)
                    if not chunk:
                        if not self.process.isalive():
                            break
                        continue
                    payload = chunk.encode("utf-8", "replace") if isinstance(chunk, str) else bytes(chunk)
                    with self._output_ready:
                        self._output_buffer.extend(payload)
                        self._output_ready.notify_all()
            except Exception:
                pass
            finally:
                with self._output_ready:
                    self._output_closed = True
                    self._output_ready.notify_all()

        def read(self, size: int = 4096) -> bytes:
            with self._output_ready:
                if not self._output_buffer and not self._output_closed:
                    self._output_ready.wait(timeout=0.05)
                if not self._output_buffer:
                    return b""
                limit = max(1, size)
                payload = bytes(self._output_buffer[:limit])
                del self._output_buffer[:limit]
                return payload

        def write(self, data: bytes) -> int:
            if not data:
                return 0
            text = _normalize_windows_input(data)
            self.process.write(text)
            return len(data)

        def resize(self, cols: int, rows: int) -> None:
            self.cols, self.rows = normalize_terminal_size(cols, rows)
            self.process.setwinsize(self.rows, self.cols)

        def poll(self) -> int | None:
            if self.process.isalive():
                return None
            if getattr(self.process, "exitstatus", None) is None:
                try:
                    return int(self.process.wait())
                except Exception:
                    return 0
            return int(self.process.exitstatus)

        def wait(self, timeout: float | None = None) -> int:
            deadline = None if timeout is None else time.perf_counter() + timeout
            while self.process.isalive():
                if deadline is not None and time.perf_counter() >= deadline:
                    raise TimeoutError("pywinpty-Prozess hat das Zeitlimit ueberschritten.")
                time.sleep(0.05)
            if getattr(self.process, "exitstatus", None) is None:
                return int(self.process.wait())
            return int(self.process.exitstatus)

        def terminate(self, force: bool = False) -> None:
            if not self.process.isalive():
                return
            self.process.terminate(force=force)

        def close(self) -> None:
            if self._closed:
                return
            self._closed = True
            proc = self.process
            try:
                if proc.isalive():
                    proc.terminate(force=True)
                    time.sleep(0.05)
            except Exception:
                pass
            try:
                proc.pty.cancel_io()
            except Exception:
                pass
            for attr in ("fileobj", "_server"):
                try:
                    resource = getattr(proc, attr, None)
                    if resource is not None:
                        resource.close()
                except Exception:
                    pass
            try:
                thread = getattr(proc, "_thread", None)
                if thread is not None and thread.is_alive():
                    thread.join(timeout=0.2)
            except Exception:
                pass
            try:
                proc.closed = False
                proc.close(force=True)
            except Exception:
                pass
            with self._output_ready:
                self._output_closed = True
                self._output_ready.notify_all()

    class _WindowsConPtyProcess(PtyProcess):
        def __init__(self, command: Sequence[str], cwd: Path, env: dict[str, str], cols: int, rows: int) -> None:
            if CreatePseudoConsole is None or ResizePseudoConsole is None or ClosePseudoConsole is None:
                raise OSError("ConPTY ist auf diesem Windows-System nicht verfuegbar.")

            self.command = [str(part) for part in command]
            self.cwd = Path(cwd)
            self.cols, self.rows = normalize_terminal_size(cols, rows)
            self.pid = 0
            self._closed = False
            self._input_handle: wintypes.HANDLE | None = None
            self._output_handle: wintypes.HANDLE | None = None
            self._process_handle: wintypes.HANDLE | None = None
            self._pseudo_console: wintypes.HANDLE | None = None
            self._output_buffer = bytearray()
            self._output_closed = False
            self._output_lock = threading.Lock()
            self._output_ready = threading.Condition(self._output_lock)

            pipe_in_read: wintypes.HANDLE | None = None
            pipe_in_write: wintypes.HANDLE | None = None
            pipe_out_read: wintypes.HANDLE | None = None
            pipe_out_write: wintypes.HANDLE | None = None
            attr_list: ctypes.c_void_p | None = None
            attr_buffer: ctypes.Array[ctypes.c_char] | None = None
            proc_info = PROCESS_INFORMATION()

            try:
                pipe_in_read, pipe_in_write = _create_pipe()
                pipe_out_read, pipe_out_write = _create_pipe()
                _set_no_inherit(pipe_in_write)
                _set_no_inherit(pipe_out_read)

                hpc = wintypes.HANDLE()
                result = int(CreatePseudoConsole(COORD(self.cols, self.rows), pipe_in_read, pipe_out_write, 0, ctypes.byref(hpc)))
                if result != 0:
                    _raise_hresult("ConPTY konnte nicht erstellt werden", result)
                self._pseudo_console = hpc

                _close_handle(pipe_in_read)
                pipe_in_read = None
                _close_handle(pipe_out_write)
                pipe_out_write = None

                self._input_handle = pipe_in_write
                pipe_in_write = None
                self._output_handle = pipe_out_read
                pipe_out_read = None

                attr_buffer, attr_list = _build_attribute_list(self._pseudo_console)
                startup = STARTUPINFOEXW()
                startup.StartupInfo.cb = ctypes.sizeof(STARTUPINFOEXW)
                startup.lpAttributeList = attr_list

                env_block = _build_environment_block(env)
                env_ptr = ctypes.cast(env_block, ctypes.c_void_p) if env_block is not None else None
                commandline = ctypes.create_unicode_buffer(subprocess.list2cmdline(self.command))
                flags = EXTENDED_STARTUPINFO_PRESENT | CREATE_UNICODE_ENVIRONMENT

                if not CreateProcessW(
                    None,
                    commandline,
                    None,
                    None,
                    False,
                    flags,
                    env_ptr,
                    str(self.cwd),
                    ctypes.byref(startup.StartupInfo),
                    ctypes.byref(proc_info),
                ):
                    _raise_last_error("ConPTY-Prozess konnte nicht gestartet werden")

                self._process_handle = proc_info.hProcess
                self.pid = int(proc_info.dwProcessId)
                _close_handle(proc_info.hThread)
                threading.Thread(target=self._capture_output, daemon=True).start()
            except Exception:
                self.close()
                raise
            finally:
                if attr_list is not None:
                    DeleteProcThreadAttributeList(attr_list)
                _close_handle(pipe_in_read)
                _close_handle(pipe_in_write)
                _close_handle(pipe_out_read)
                _close_handle(pipe_out_write)

        def read(self, size: int = 4096) -> bytes:
            with self._output_ready:
                if not self._output_buffer and not self._output_closed:
                    self._output_ready.wait(timeout=0.05)
                if not self._output_buffer:
                    return b""
                limit = max(1, size)
                payload = bytes(self._output_buffer[:limit])
                del self._output_buffer[:limit]
                return payload

        def write(self, data: bytes) -> int:
            if self._input_handle is None or not data:
                return 0
            payload_text = _normalize_windows_input(data).encode("utf-8", "replace")
            payload = ctypes.create_string_buffer(payload_text)
            written = wintypes.DWORD()
            if not WriteFile(self._input_handle, payload, len(payload_text), ctypes.byref(written), None):
                _raise_last_error("ConPTY-Eingabe konnte nicht geschrieben werden")
            return int(written.value)

        def resize(self, cols: int, rows: int) -> None:
            if self._pseudo_console is None:
                return
            self.cols, self.rows = normalize_terminal_size(cols, rows)
            result = int(ResizePseudoConsole(self._pseudo_console, COORD(self.cols, self.rows)))
            if result != 0:
                _raise_hresult("ConPTY konnte nicht skaliert werden", result)

        def poll(self) -> int | None:
            if self._process_handle is None:
                return None
            result = WaitForSingleObject(self._process_handle, 0)
            if result == WAIT_TIMEOUT:
                return None
            if result != WAIT_OBJECT_0:
                _raise_last_error("Prozessstatus konnte nicht gelesen werden")
            code = wintypes.DWORD()
            if not GetExitCodeProcess(self._process_handle, ctypes.byref(code)):
                _raise_last_error("Exit-Code konnte nicht gelesen werden")
            return None if code.value == STILL_ACTIVE else int(code.value)

        def wait(self, timeout: float | None = None) -> int:
            if self._process_handle is None:
                return 0
            milliseconds = 0xFFFFFFFF if timeout is None else max(0, int(timeout * 1000))
            result = WaitForSingleObject(self._process_handle, milliseconds)
            if result == WAIT_TIMEOUT:
                raise TimeoutError("ConPTY-Prozess hat das Zeitlimit ueberschritten.")
            if result != WAIT_OBJECT_0:
                _raise_last_error("Auf den ConPTY-Prozess konnte nicht gewartet werden")
            exit_code = self.poll()
            return int(exit_code or 0)

        def terminate(self, force: bool = False) -> None:
            if self.poll() is not None:
                return
            if not force:
                try:
                    self.write(b"\x03")
                except Exception:
                    pass
                deadline = time.perf_counter() + 1.2
                while time.perf_counter() < deadline:
                    if self.poll() is not None:
                        return
                    time.sleep(0.05)
            if self._process_handle is not None and self.poll() is None:
                if not TerminateProcess(self._process_handle, 1):
                    _raise_last_error("ConPTY-Prozess konnte nicht beendet werden")

        def _capture_output(self) -> None:
            if self._output_handle is None:
                return
            buffer = ctypes.create_string_buffer(4096)
            try:
                while True:
                    read = wintypes.DWORD()
                    ok = ReadFile(self._output_handle, buffer, len(buffer), ctypes.byref(read), None)
                    if not ok or read.value == 0:
                        break
                    with self._output_ready:
                        self._output_buffer.extend(buffer.raw[: read.value])
                        self._output_ready.notify_all()
            finally:
                with self._output_ready:
                    self._output_closed = True
                    self._output_ready.notify_all()

        def close(self) -> None:
            if self._closed:
                return
            self._closed = True
            if self._output_handle is not None:
                _close_handle(self._output_handle)
                self._output_handle = None
            if self._input_handle is not None:
                _close_handle(self._input_handle)
                self._input_handle = None
            if self._process_handle is not None:
                _close_handle(self._process_handle)
                self._process_handle = None
            if self._pseudo_console is not None:
                ClosePseudoConsole(self._pseudo_console)
                self._pseudo_console = None


else:
    import errno
    import fcntl
    import pty
    import struct
    import termios

    class _PosixPtyProcess(PtyProcess):
        def __init__(self, command: Sequence[str], cwd: Path, env: dict[str, str], cols: int, rows: int) -> None:
            self.command = [str(part) for part in command]
            self.cwd = Path(cwd)
            self.cols, self.rows = normalize_terminal_size(cols, rows)
            self._closed = False
            self._master_fd, slave_fd = pty.openpty()
            self.resize(self.cols, self.rows)
            try:
                self.process = subprocess.Popen(
                    self.command,
                    cwd=str(self.cwd),
                    env=env,
                    stdin=slave_fd,
                    stdout=slave_fd,
                    stderr=slave_fd,
                    shell=False,
                    close_fds=True,
                    start_new_session=True,
                )
            finally:
                os.close(slave_fd)
            self.pid = int(self.process.pid)

        def read(self, size: int = 4096) -> bytes:
            try:
                return os.read(self._master_fd, max(1, size))
            except OSError as exc:
                if exc.errno == errno.EIO:
                    return b""
                raise

        def write(self, data: bytes) -> int:
            if not data:
                return 0
            return os.write(self._master_fd, data)

        def resize(self, cols: int, rows: int) -> None:
            self.cols, self.rows = normalize_terminal_size(cols, rows)
            winsize = struct.pack("HHHH", self.rows, self.cols, 0, 0)
            fcntl.ioctl(self._master_fd, termios.TIOCSWINSZ, winsize)

        def poll(self) -> int | None:
            return self.process.poll()

        def wait(self, timeout: float | None = None) -> int:
            return int(self.process.wait(timeout=timeout))

        def terminate(self, force: bool = False) -> None:
            if self.poll() is not None:
                return
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.killpg(self.process.pid, sig)
            if not force:
                deadline = time.perf_counter() + 1.2
                while time.perf_counter() < deadline:
                    if self.poll() is not None:
                        return
                    time.sleep(0.05)
                if self.poll() is None:
                    os.killpg(self.process.pid, signal.SIGKILL)

        def close(self) -> None:
            if self._closed:
                return
            self._closed = True
            try:
                os.close(self._master_fd)
            except OSError:
                pass


def create_pty_process(command: Sequence[str], cwd: Path, env: dict[str, str], cols: int | None = None, rows: int | None = None) -> PtyProcess:
    width, height = normalize_terminal_size(cols, rows)
    if os.name == "nt":
        if WinptyProcess is not None:
            return _PyWinPtyProcess(command, cwd, env, width, height)
        return _WindowsConPtyProcess(command, cwd, env, width, height)
    return _PosixPtyProcess(command, cwd, env, width, height)

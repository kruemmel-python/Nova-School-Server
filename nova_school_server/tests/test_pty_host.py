from __future__ import annotations

import importlib.util
import os
import shutil
import time
import unittest
from pathlib import Path

from nova_school_server.pty_host import create_pty_process


class PtyHostTests(unittest.TestCase):
    def test_pty_process_handles_prompt_input_and_resize(self) -> None:
        if os.name == "nt" and importlib.util.find_spec("winpty") is None:
            self.skipTest("pywinpty ist fuer Windows-PTY-Tests nicht installiert")
        executable = shutil.which("python") or shutil.which("py")
        if not executable:
            self.skipTest("python ist fuer den PTY-Test nicht verfuegbar")

        command = [executable, "-u", "-c", "name = input('Name: ')\nprint(f'Hallo {name}!')\n"]
        if Path(executable).name.lower() in {"py", "py.exe"}:
            command = [executable, "-3", "-u", "-c", "name = input('Name: ')\nprint(f'Hallo {name}!')\n"]

        env = dict(os.environ)
        env["PYTHONUTF8"] = "1"
        pty = create_pty_process(command, Path.cwd(), env, 90, 24)
        transcript = ""

        try:
            deadline = time.time() + 8
            while time.time() < deadline and "Name:" not in transcript:
                chunk = pty.read(2048).decode("utf-8", "replace")
                transcript += chunk
                if "Name:" in transcript:
                    break
                time.sleep(0.05)

            self.assertIn("Name:", transcript)
            pty.resize(110, 32)
            pty.write(b"Nova\r")

            deadline = time.time() + 8
            while time.time() < deadline:
                chunk = pty.read(2048).decode("utf-8", "replace")
                if chunk:
                    transcript += chunk
                if "Hallo Nova!" in transcript and pty.poll() is not None:
                    break
                time.sleep(0.05)

            self.assertIn("Hallo Nova!", transcript)
            self.assertEqual(pty.wait(timeout=3), 0)
        finally:
            try:
                if pty.poll() is None:
                    pty.terminate(force=True)
            finally:
                pty.close()


if __name__ == "__main__":
    unittest.main()

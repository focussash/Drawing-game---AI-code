"""Optional public link: an SSH reverse tunnel through localhost.run (free, no account).

The tunnel runs in the same console as the server, so closing the window stops
both; if the tunnel drops on its own, the caller stops the server too.
"""

from __future__ import annotations

import subprocess
import threading
import time
from typing import Callable

TUNNEL_TARGET = "nokey@localhost.run"
LOOPBACK = "127.0.0.1"  # not "localhost": on Windows that resolves to ::1 first
READY_TIMEOUT_SECONDS = 15


def tunnel_command(port: int) -> list[str]:
    return [
        "ssh",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ServerAliveInterval=30",
        "-R", f"80:{LOOPBACK}:{port}",
        TUNNEL_TARGET,
    ]


class Tunnel:
    def __init__(self, port: int, command: list[str] | None = None):
        self.command = command or tunnel_command(port)
        self._proc: subprocess.Popen | None = None

    def start_when_ready(self, server, on_exit: Callable[[int | None], None]) -> None:
        """Once the uvicorn server is listening, run ssh; call on_exit(returncode) when it ends."""

        def run() -> None:
            deadline = time.monotonic() + READY_TIMEOUT_SECONDS
            while not server.started and not server.should_exit and time.monotonic() < deadline:
                time.sleep(0.1)
            if not server.started or server.should_exit:
                on_exit(None)
                return
            # Inherits this console, so localhost.run's welcome text and URL show up here.
            self._proc = subprocess.Popen(self.command)
            on_exit(self._proc.wait())

        threading.Thread(target=run, name="tunnel", daemon=True).start()

    def stop(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()

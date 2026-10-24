import os
import subprocess
import sys
from pathlib import Path

import pytest

import main
from server.net.tunnel import tunnel_command

ROOT = Path(__file__).resolve().parents[2]


def test_tunnel_forwards_to_ipv4_loopback_on_configured_port():
    # On Windows "localhost" resolves to ::1 first, but the server listens on
    # IPv4 only, so a tunnel aimed at "localhost" gets 502 "no tunnel".
    cmd = tunnel_command(9000)
    assert cmd[0] == "ssh" and "-R" in cmd
    assert cmd[cmd.index("-R") + 1] == "80:127.0.0.1:9000"
    assert not any("localhost:" in part for part in cmd)


def test_online_script_runs_everything_in_one_window():
    script = (ROOT / "start-online.bat").read_text(encoding="utf-8")
    assert "main.py --online" in script
    assert "ssh" not in script and "start " not in script


LAUNCHERS = ["start-server.bat", "start-online.bat"]
FINDER = ROOT / "scripts" / "find-python.bat"


def test_launchers_find_python_instead_of_hardcoding_a_path():
    for name in LAUNCHERS:
        script = (ROOT / name).read_text(encoding="utf-8")
        assert "scripts\\find-python.bat" in script, name
        assert '"%PY%" main.py' in script, name
        assert ":\\" not in script, name  # no absolute path from someone's machine


def test_finder_looks_for_the_env_that_environment_yml_creates():
    env_line = next(line for line in (ROOT / "environment.yml").read_text(encoding="utf-8").splitlines()
                    if line.startswith("name:"))
    env_name = env_line.split(":", 1)[1].strip()
    assert f'set "NHWC_ENV={env_name}"' in FINDER.read_text(encoding="utf-8")


def test_local_python_path_file_is_not_committed():
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "python-path.txt" in ignored


def _run_finder(folder: Path, python_path: str) -> subprocess.CompletedProcess:
    (folder / "python-path.txt").write_text(python_path + "\n", encoding="utf-8")
    wrapper = folder / "run.bat"
    wrapper.write_bytes((
        "@echo off\r\nchcp 65001 >nul\r\n"
        f'call "{FINDER}" "%~dp0"\r\n'
        "if errorlevel 1 exit /b 1\r\n"
        "echo PY=%PY%\r\n"
    ).encode("utf-8"))
    return subprocess.run(["cmd", "/c", "run.bat"], cwd=folder, capture_output=True, timeout=60)


windows_only = pytest.mark.skipif(os.name != "nt", reason="batch files run on Windows only")


@windows_only
def test_finder_uses_python_path_txt(tmp_path):
    result = _run_finder(tmp_path, f'"{sys.executable}"')  # quotes pasted along with the path are fine
    out = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 0, out
    assert f"PY={sys.executable}" in out


@windows_only
def test_finder_explains_a_wrong_python_path_txt(tmp_path):
    result = _run_finder(tmp_path, str(tmp_path / "nope" / "python.exe"))
    out = result.stdout.decode("utf-8", errors="replace")
    assert result.returncode == 1
    assert "python-path.txt" in out and "environment.yml" in out


def _capture_serve(monkeypatch):
    calls = []
    monkeypatch.setattr(main, "_serve", lambda app, host, port, online: calls.append((host, port, online)))
    return calls


def test_online_mode_listens_on_loopback_only(tmp_path, monkeypatch):
    calls = _capture_serve(monkeypatch)
    cfg = tmp_path / "config.toml"
    cfg.write_text("[server]\nport = 8123\n", encoding="utf-8")
    main.main(["--config", str(cfg), "--online"])
    assert calls == [("127.0.0.1", 8123, True)]


def test_normal_mode_uses_configured_host(tmp_path, monkeypatch):
    calls = _capture_serve(monkeypatch)
    cfg = tmp_path / "config.toml"
    cfg.write_text("", encoding="utf-8")
    main.main(["--config", str(cfg)])
    assert calls == [("0.0.0.0", 8000, False)]


class _FakeServer:
    def __init__(self, started):
        self.started = started
        self.should_exit = False


def _wait_for(calls, timeout=10):
    import time
    end = time.monotonic() + timeout
    while not calls and time.monotonic() < end:
        time.sleep(0.05)
    return calls


def test_tunnel_runs_once_server_is_up_and_reports_exit():
    import sys
    from server.net.tunnel import Tunnel

    calls = []
    tunnel = Tunnel(8000, command=[sys.executable, "-c", "raise SystemExit(3)"])
    tunnel.start_when_ready(_FakeServer(started=True), calls.append)
    assert _wait_for(calls) == [3]


def test_tunnel_gives_up_if_server_is_shutting_down():
    from server.net.tunnel import Tunnel

    calls = []
    server = _FakeServer(started=False)
    server.should_exit = True
    Tunnel(8000, command=["never-run"]).start_when_ready(server, calls.append)
    assert _wait_for(calls) == [None]

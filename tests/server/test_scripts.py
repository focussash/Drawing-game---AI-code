from pathlib import Path

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

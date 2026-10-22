from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_tunnel_forwards_to_ipv4_loopback():
    # On Windows "localhost" resolves to ::1 first, but the server listens on
    # IPv4 only, so a tunnel aimed at "localhost" gets 502 "no tunnel".
    script = (ROOT / "start-online.bat").read_text(encoding="utf-8")
    assert "-R 80:127.0.0.1:8000" in script
    assert ":localhost:" not in script

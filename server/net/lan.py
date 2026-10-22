"""Find this machine's LAN address so phones on the same Wi-Fi know where to connect."""

from __future__ import annotations

import socket


def lan_ip() -> str | None:
    # Connecting a UDP socket sends nothing; it only makes the OS pick the outgoing interface.
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ip = s.getsockname()[0]
    except OSError:
        return None
    return None if ip.startswith("127.") or ip == "0.0.0.0" else ip

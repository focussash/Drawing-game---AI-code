"""Chat history kept with each entry's audience, for reconnect snapshots."""

from __future__ import annotations

from collections import deque

from server.audience import Audience


class ChatLog:
    def __init__(self, limit: int):
        self._entries: deque[tuple[Audience, dict]] = deque(maxlen=limit)

    def append(self, audience: Audience, entry: dict) -> None:
        self._entries.append((audience, entry))

    def visible_to(self, pid: str) -> list[dict]:
        return [entry for audience, entry in self._entries if audience.includes(pid)]

    def clear(self) -> None:
        self._entries.clear()

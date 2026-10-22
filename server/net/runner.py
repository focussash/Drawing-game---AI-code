"""Drives one room: wakes on deadlines or new input, ticks the room, sends its output."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Callable

from server.clock import Clock
from server.net.connection import Connection
from server.protocol_limits import CLOSE_KICKED
from server.room import Room

log = logging.getLogger(__name__)

MAX_SLEEP_SECONDS = 1.0  # also how often abandonment is checked


class RoomRunner:
    def __init__(self, room: Room, clock: Clock, on_done: Callable[[], None]):
        self.room = room
        self._clock = clock
        self._on_done = on_done
        self._wake = asyncio.Event()
        self.connections: dict[str, Connection] = {}

    def bind(self, pid: str, conn: Connection) -> Connection | None:
        old = self.connections.get(pid)
        self.connections[pid] = conn
        return old if old is not conn else None

    def unbind(self, pid: str, conn: Connection) -> bool:
        """Forget conn only if it is still the player's current connection."""
        if self.connections.get(pid) is conn:
            del self.connections[pid]
            return True
        return False

    def flush(self) -> None:
        for audience, msg in self.room.drain_outbox():
            text = json.dumps(msg, ensure_ascii=False)
            for pid, conn in self.connections.items():
                if audience.includes(pid):
                    conn.send(text)
        for pid in self.room.drain_closes():
            conn = self.connections.pop(pid, None)
            if conn is not None:
                conn.close(CLOSE_KICKED)

    def poke(self) -> None:
        self._wake.set()

    async def run(self) -> None:
        while True:
            deadline = self.room.next_deadline()
            timeout = MAX_SLEEP_SECONDS
            if deadline is not None:
                timeout = min(timeout, max(0.0, deadline - self._clock.now()))
            try:
                await asyncio.wait_for(self._wake.wait(), timeout)
            except TimeoutError:
                pass
            self._wake.clear()
            try:
                self.room.tick()
                self.flush()
                if self.room.is_abandoned():
                    self._on_done()
                    return
            except Exception:
                log.exception("room %s: tick failed", self.room.code)

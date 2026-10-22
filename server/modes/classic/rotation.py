"""Turn order: everyone draws once per round, in join order; late joiners go to the end."""

from __future__ import annotations

from typing import Callable


class Rotation:
    def __init__(self, rounds: int):
        self.rounds = rounds
        self.round = 0
        self._queue: list[str] = []
        self._drawn: set[str] = set()  # popped this round, drew or skipped

    def start(self, ids: list[str]) -> None:
        self.round = 1
        self._queue = list(ids)
        self._drawn = set()

    def add_late(self, pid: str) -> None:
        if pid not in self._queue and pid not in self._drawn:
            self._queue.append(pid)

    def remove(self, pid: str) -> None:
        if pid in self._queue:
            self._queue.remove(pid)

    def next_drawer(self, ids: list[str], eligible: Callable[[str], bool]) -> str | None:
        while True:
            while self._queue:
                pid = self._queue.pop(0)
                self._drawn.add(pid)
                if eligible(pid):
                    return pid
            if self.round >= self.rounds:
                return None
            self.round += 1
            self._queue = list(ids)
            self._drawn = set()

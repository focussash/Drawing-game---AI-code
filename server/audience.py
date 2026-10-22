"""Who receives an outgoing message."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Audience:
    only: frozenset[str] | None = None  # None means everyone in the room
    exclude: frozenset[str] = frozenset()

    @classmethod
    def everyone(cls) -> Audience:
        return cls()

    @classmethod
    def of(cls, *pids: str) -> Audience:
        return cls(only=frozenset(pids))

    @classmethod
    def all_except(cls, *pids: str) -> Audience:
        return cls(exclude=frozenset(pids))

    def includes(self, pid: str) -> bool:
        if pid in self.exclude:
            return False
        return self.only is None or pid in self.only

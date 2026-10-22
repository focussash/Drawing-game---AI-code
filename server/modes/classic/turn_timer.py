"""Countdown for one drawing turn, with shortening and drawer-requested extensions."""

from __future__ import annotations


class TurnTimer:
    def __init__(self) -> None:
        self.deadline: float | None = None
        self.extends_used = 0

    def start(self, now: float, seconds: float) -> None:
        self.deadline = now + seconds
        self.extends_used = 0

    def remaining(self, now: float) -> float:
        if self.deadline is None:
            return 0.0
        return max(0.0, self.deadline - now)

    def shorten_to(self, now: float, seconds: float) -> None:
        self.deadline = min(self.deadline, now + seconds)

    def extend(self, seconds: float) -> None:
        self.deadline += seconds
        self.extends_used += 1

    def expired(self, now: float) -> bool:
        return self.deadline is not None and now >= self.deadline

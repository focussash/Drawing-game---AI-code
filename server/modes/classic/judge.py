"""Is a chat message a correct guess?"""

from __future__ import annotations

from server.textnorm import normalize


def is_correct(guess: str, answer: str) -> bool:
    # Containment, so "是不是长颈鹿" counts and never leaks the answer publicly.
    target = normalize(answer)
    return bool(target) and target in normalize(guess)

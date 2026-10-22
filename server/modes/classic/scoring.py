"""Classic mode scoring. Faster guesses score more; revealed characters discount everyone after."""

from __future__ import annotations

from server.modes.classic.settings import ScoringConfig


def guesser_points(remaining: float, draw_seconds: int, reveals: int, cfg: ScoringConfig) -> int:
    ratio = min(1.0, remaining / draw_seconds)
    base = max(cfg.guesser_min, cfg.guesser_max * ratio)
    return round(base * cfg.reveal_factor ** reveals)


def drawer_points(reveals: int, cfg: ScoringConfig) -> int:
    return round(cfg.drawer_per_guess * cfg.reveal_factor ** reveals)

"""Lobby state: the host's settings for the next game and the last game's results."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from server.modes.base import SettingSpec, defaults_from, validate_settings
from server.wordbank import list_banks


class LobbyState:
    def __init__(self, specs_fn: Callable[[list[str]], list[SettingSpec]], words_dir: Path):
        self._specs_fn = specs_fn
        self._words_dir = words_dir
        self.banks = list_banks(words_dir)
        self.specs = specs_fn(self.banks)
        self.values = defaults_from(self.specs)
        self.last_results: list[dict] | None = None

    def refresh_banks(self) -> list[str]:
        """Rescan the words folder; drop selected banks whose files are gone."""
        self.banks = list_banks(self._words_dir)
        self.specs = self._specs_fn(self.banks)
        if "banks" in self.values:
            kept = [b for b in self.values["banks"] if b in self.banks]
            self.values["banks"] = kept or defaults_from(self.specs)["banks"]
        return self.banks

    def update(self, updates: dict) -> None:
        self.values = validate_settings(self.specs, self.values, updates, self.banks)

    def message(self) -> dict:
        return {"type": "lobby", "specs": [s.to_json() for s in self.specs], "values": dict(self.values),
                "banks": list(self.banks), "last_results": self.last_results}

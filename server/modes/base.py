"""The contract between the room core and a game mode.

The core (rooms, connections, canvas, chat transport) knows nothing about
rules. A mode decides phases, who sees what, how chat is judged and scored,
and which settings the host can tweak in the lobby.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, ClassVar, Literal, Protocol

from server.audience import Audience
from server.config import RoomConfig
from server.wordbank import WordPool

SettingKind = Literal["int", "bool", "banks"]


@dataclass(frozen=True)
class SettingSpec:
    key: str
    label: str
    kind: SettingKind
    default: Any
    min: int | None = None
    max: int | None = None

    def to_json(self) -> dict:
        default = list(self.default) if self.kind == "banks" else self.default
        return {"key": self.key, "label": self.label, "kind": self.kind,
                "default": default, "min": self.min, "max": self.max}


class SettingsError(Exception):
    def __init__(self, key: str, message: str):
        super().__init__(f"{key}: {message}")
        self.key = key
        self.message = message


def defaults_from(specs: list[SettingSpec]) -> dict:
    return {s.key: (list(s.default) if s.kind == "banks" else s.default) for s in specs}


def validate_settings(specs: list[SettingSpec], current: dict, updates: dict, banks: list[str]) -> dict:
    by_key = {s.key: s for s in specs}
    result = dict(current)
    for key, value in updates.items():
        spec = by_key.get(key)
        if spec is None:
            raise SettingsError(key, "没有这个设置项")
        result[key] = _check(spec, value, banks)
    return result


def _check(spec: SettingSpec, value: Any, banks: list[str]) -> Any:
    if spec.kind == "bool":
        if not isinstance(value, bool):
            raise SettingsError(spec.key, "必须是开或关")
        return value
    if spec.kind == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            raise SettingsError(spec.key, "必须是整数")
        if (spec.min is not None and value < spec.min) or (spec.max is not None and value > spec.max):
            raise SettingsError(spec.key, f"必须在 {spec.min}..{spec.max} 之间")
        return value
    if spec.kind == "banks":
        if not isinstance(value, list) or not value or not all(isinstance(v, str) for v in value):
            raise SettingsError(spec.key, "至少选一个词库")
        missing = [v for v in value if v not in banks]
        if missing:
            raise SettingsError(spec.key, f"词库不存在: {'、'.join(missing)}")
        return list(dict.fromkeys(value))
    raise SettingsError(spec.key, "未知的设置类型")


class ModeContext(Protocol):
    """What a mode may ask of, or do to, its room."""

    def player_ids(self) -> list[str]: ...           # join order, offline players included
    def is_online(self, pid: str) -> bool: ...
    def is_away(self, pid: str) -> bool: ...          # offline for at least away_after_seconds
    def is_host(self, pid: str) -> bool: ...
    def nickname(self, pid: str) -> str: ...
    def send(self, audience: Audience, msg: dict) -> None: ...
    def post_chat(self, audience: Audience, entry: dict) -> None: ...
    def clear_canvas(self) -> None: ...
    def room_config(self) -> RoomConfig: ...
    def finish(self, results: list[dict]) -> None: ...


class Mode(ABC):
    name: ClassVar[str]

    @classmethod
    @abstractmethod
    def parse_mode_config(cls, raw: dict) -> Any:
        """Validate this mode's [modes.<name>] section; raise ConfigError."""

    @classmethod
    @abstractmethod
    def setting_specs(cls, mode_cfg: Any, banks: list[str]) -> list[SettingSpec]:
        """Lobby settings the host can change, with defaults from mode_cfg."""

    def __init__(self, ctx: ModeContext, settings: dict, mode_cfg: Any, words: WordPool, rng: random.Random):
        self.ctx = ctx
        self.settings = settings
        self.mode_cfg = mode_cfg
        self.words = words
        self.rng = rng

    @abstractmethod
    def start(self, now: float) -> None: ...

    @abstractmethod
    def on_chat(self, pid: str, text: str, now: float) -> None: ...

    @abstractmethod
    def on_action(self, pid: str, name: str, data: dict, now: float) -> None: ...

    @abstractmethod
    def on_tick(self, now: float) -> None: ...

    @abstractmethod
    def next_deadline(self) -> float | None: ...

    @abstractmethod
    def on_player_joined(self, pid: str, now: float) -> None: ...

    @abstractmethod
    def on_player_offline(self, pid: str, now: float) -> None: ...

    @abstractmethod
    def on_player_online(self, pid: str, now: float) -> None: ...

    @abstractmethod
    def on_player_removed(self, pid: str, now: float) -> None: ...

    @abstractmethod
    def can_draw(self, pid: str) -> bool: ...

    @abstractmethod
    def snapshot_for(self, pid: str, now: float) -> dict: ...

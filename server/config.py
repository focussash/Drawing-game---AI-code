"""Load and validate config.toml into frozen dataclasses.

Mode sections ([modes.<name>]) are kept raw here; each mode validates its own
section (see server.modes.parse_mode_configs).
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any


class ConfigError(Exception):
    """Raised when config.toml is invalid; the message names the offending key."""


@dataclass(frozen=True)
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8000


@dataclass(frozen=True)
class RoomConfig:
    max_players: int = 12
    min_players: int = 2
    away_after_seconds: int = 60
    drawer_offline_skip_seconds: int = 15
    empty_room_ttl_seconds: int = 600
    chat_history: int = 100
    max_chat_length: int = 60
    max_nickname_length: int = 12


@dataclass(frozen=True)
class DrawingConfig:
    colors: tuple[str, ...] = (
        "#000000", "#e53935", "#fb8c00", "#fdd835", "#43a047", "#1e88e5", "#795548",
    )
    brush_sizes: tuple[int, ...] = (4, 8, 16, 32)
    eraser_sizes: tuple[int, ...] = (16, 32, 64)


@dataclass(frozen=True)
class AppConfig:
    server: ServerConfig
    room: RoomConfig
    drawing: DrawingConfig
    words_dir: Path
    modes: dict[str, dict] = field(default_factory=dict)


_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_SECTIONS = {"server", "room", "words", "drawing", "modes"}


def load_config(path: Path) -> AppConfig:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError as e:
        raise ConfigError(f"无法读取配置文件 {path}: {e}") from e
    return parse_config(text, path.parent)


def parse_config(text: str, base_dir: Path) -> AppConfig:
    try:
        raw = tomllib.loads(text)
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"config.toml 格式错误: {e}") from e

    for name in raw:
        if name not in _SECTIONS:
            raise ConfigError(f"未知的配置节: [{name}]（{name}）")

    server = _build(ServerConfig, raw.get("server", {}), "server")
    room = _build(RoomConfig, raw.get("room", {}), "room")
    drawing = _build(DrawingConfig, raw.get("drawing", {}), "drawing")
    words_dir = _words_dir(raw.get("words", {}), Path(base_dir))
    modes = _modes(raw.get("modes", {}))

    _check_room(room)
    _check_drawing(drawing)
    _require(server.port <= 65535, "server.port", "必须在 1..65535 之间")
    return AppConfig(server=server, room=room, drawing=drawing, words_dir=words_dir, modes=modes)


def _build(cls: type, section: Any, prefix: str):
    if not isinstance(section, dict):
        raise ConfigError(f"[{prefix}] 必须是一个配置节（{prefix}）")
    known = {f.name: f for f in fields(cls)}
    for key in section:
        if key not in known:
            raise ConfigError(f"未知的配置项: {prefix}.{key}")
    values = {}
    for key, value in section.items():
        default = getattr(cls(), key)
        values[key] = _coerce(value, default, f"{prefix}.{key}")
    return cls(**values)


def _coerce(value: Any, default: Any, key: str) -> Any:
    if isinstance(default, bool):
        _require(isinstance(value, bool), key, "必须是 true 或 false")
        return value
    if isinstance(default, int):
        _require(isinstance(value, int) and not isinstance(value, bool), key, "必须是整数")
        _require(value > 0, key, "必须是正整数")
        return value
    if isinstance(default, str):
        _require(isinstance(value, str), key, "必须是字符串")
        return value
    if isinstance(default, tuple):
        _require(isinstance(value, list) and len(value) > 0, key, "必须是非空列表")
        item_default = default[0]
        return tuple(_coerce(v, item_default, key) for v in value)
    raise ConfigError(f"不支持的配置项类型: {key}")


def _words_dir(section: Any, base_dir: Path) -> Path:
    if not isinstance(section, dict):
        raise ConfigError("[words] 必须是一个配置节（words）")
    for key in section:
        if key != "dir":
            raise ConfigError(f"未知的配置项: words.{key}")
    d = section.get("dir", "words")
    _require(isinstance(d, str) and d.strip() != "", "words.dir", "必须是非空字符串")
    return base_dir / d


def _modes(section: Any) -> dict[str, dict]:
    if not isinstance(section, dict):
        raise ConfigError("[modes] 必须是一个配置节（modes）")
    for name, value in section.items():
        _require(isinstance(value, dict), f"modes.{name}", "必须是一个配置节")
    return dict(section)


def _check_room(room: RoomConfig) -> None:
    _require(room.min_players >= 2, "room.min_players", "至少为 2")
    _require(room.min_players <= room.max_players, "room.min_players", "不能大于 max_players")


def _check_drawing(drawing: DrawingConfig) -> None:
    for c in drawing.colors:
        _require(bool(_COLOR_RE.match(c)), "drawing.colors", f"颜色 {c!r} 必须是 #rrggbb 格式")


def _require(ok: bool, key: str, message: str) -> None:
    if not ok:
        raise ConfigError(f"{key}: {message}")

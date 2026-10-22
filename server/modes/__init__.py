"""Registry of game modes. A new mode = a new subpackage + one entry here."""

from __future__ import annotations

from typing import Any

from server.config import ConfigError
from server.modes.base import Mode

MODES: dict[str, type[Mode]] = {}


def parse_mode_configs(raw: dict[str, dict]) -> dict[str, Any]:
    for name in raw:
        if name not in MODES:
            raise ConfigError(f"未知的模式: [modes.{name}]（{name}）")
    return {name: cls.parse_mode_config(raw.get(name, {})) for name, cls in MODES.items()}

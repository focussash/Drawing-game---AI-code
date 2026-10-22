"""Classic mode: the [modes.classic] config section and lobby setting specs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from server.config import ConfigError
from server.modes.base import SettingSpec


@dataclass(frozen=True)
class ScoringConfig:
    guesser_max: int = 100
    guesser_min: int = 20
    drawer_per_guess: int = 25
    reveal_factor: float = 0.75


@dataclass(frozen=True)
class ClassicConfig:
    defaults: dict
    scoring: ScoringConfig
    default_banks: tuple[str, ...]


# (key, label, kind, min, max, built-in default)
_SETTINGS: list[tuple[str, str, str, int | None, int | None, Any]] = [
    ("rounds", "圈数", "int", 1, 10, 3),
    ("draw_seconds", "作画时长（秒）", "int", 30, 300, 80),
    ("choose_seconds", "选词时长（秒）", "int", 5, 60, 15),
    ("word_choices", "候选词数量", "int", 1, 5, 3),
    ("show_length_hint", "显示字数", "bool", None, None, True),
    ("shorten_after_first_correct", "有人猜对后缩短倒计时", "bool", None, None, True),
    ("shorten_to_seconds", "缩短到（秒）", "int", 5, 60, 20),
    ("extend_seconds", "每次加时（秒）", "int", 5, 60, 10),
    ("max_extends_per_turn", "每轮最多加时次数", "int", 0, 10, 3),
    ("reveal_seconds", "公布答案停留（秒）", "int", 3, 20, 6),
]
_DEFAULT_BANKS = ("默认",)


def parse_classic_config(raw: dict) -> ClassicConfig:
    known = {row[0] for row in _SETTINGS} | {"default_banks", "scoring"}
    for key in raw:
        if key not in known:
            raise ConfigError(f"未知的配置项: modes.classic.{key}")

    defaults = {}
    for key, _label, kind, lo, hi, builtin in _SETTINGS:
        value = raw.get(key, builtin)
        name = f"modes.classic.{key}"
        if kind == "bool":
            _require(isinstance(value, bool), name, "必须是 true 或 false")
        else:
            _require(isinstance(value, int) and not isinstance(value, bool), name, "必须是整数")
            _require(lo <= value <= hi, name, f"必须在 {lo}..{hi} 之间")
        defaults[key] = value

    banks = raw.get("default_banks", list(_DEFAULT_BANKS))
    _require(isinstance(banks, list) and all(isinstance(b, str) for b in banks),
             "modes.classic.default_banks", "必须是字符串列表")

    return ClassicConfig(defaults=defaults, scoring=_parse_scoring(raw.get("scoring", {})),
                         default_banks=tuple(banks))


def _parse_scoring(raw: Any) -> ScoringConfig:
    _require(isinstance(raw, dict), "modes.classic.scoring", "必须是一个配置节")
    base = ScoringConfig()
    values = {}
    for key, value in raw.items():
        name = f"modes.classic.scoring.{key}"
        _require(hasattr(base, key), name, "未知的配置项")
        if key == "reveal_factor":
            _require(isinstance(value, (int, float)) and not isinstance(value, bool) and 0 < value <= 1,
                     name, "必须满足 0 < reveal_factor ≤ 1")
            values[key] = float(value)
        else:
            _require(isinstance(value, int) and not isinstance(value, bool) and value > 0, name, "必须是正整数")
            values[key] = value
    scoring = ScoringConfig(**values)
    _require(scoring.guesser_min <= scoring.guesser_max, "modes.classic.scoring.guesser_min",
             "不能大于 guesser_max")
    return scoring


def classic_setting_specs(cfg: ClassicConfig, banks: list[str]) -> list[SettingSpec]:
    chosen = [b for b in cfg.default_banks if b in banks] or banks[:1]
    specs = [SettingSpec("banks", "词库", "banks", tuple(chosen))]
    for key, label, kind, lo, hi, _builtin in _SETTINGS:
        specs.append(SettingSpec(key, label, kind, cfg.defaults[key], lo, hi))
    return specs


def _require(ok: bool, key: str, message: str) -> None:
    if not ok:
        raise ConfigError(f"{key}: {message}")

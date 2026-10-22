import pytest

from server.config import ConfigError
from server.modes import parse_mode_configs
from server.modes.base import SettingsError, defaults_from, validate_settings
from server.modes.classic.settings import classic_setting_specs, parse_classic_config

BANKS = ["默认", "动物"]


def specs():
    return classic_setting_specs(parse_classic_config({}), banks=BANKS)


def test_defaults():
    d = defaults_from(specs())
    assert d["rounds"] == 3 and d["draw_seconds"] == 80 and d["banks"] == ["默认"]
    assert d["extend_seconds"] == 10 and d["max_extends_per_turn"] == 3


def test_config_values_become_defaults():
    s = classic_setting_specs(parse_classic_config({"rounds": 5, "show_length_hint": False}), BANKS)
    d = defaults_from(s)
    assert d["rounds"] == 5 and d["show_length_hint"] is False


def test_banks_default_falls_back_to_first():
    s = classic_setting_specs(parse_classic_config({}), banks=["动物"])
    assert defaults_from(s)["banks"] == ["动物"]


def test_banks_default_empty_when_no_banks():
    assert defaults_from(classic_setting_specs(parse_classic_config({}), banks=[]))["banks"] == []


def test_partial_update_keeps_others():
    cur = defaults_from(specs())
    new = validate_settings(specs(), cur, {"rounds": 5}, BANKS)
    assert new["rounds"] == 5 and new["draw_seconds"] == 80 and cur["rounds"] == 3


def test_spec_json_shape():
    rounds = next(s for s in specs() if s.key == "rounds")
    assert rounds.to_json() == {"key": "rounds", "label": "圈数", "kind": "int", "default": 3, "min": 1, "max": 10}


@pytest.mark.parametrize("updates, key", [
    ({"rounds": 0}, "rounds"), ({"rounds": "5"}, "rounds"), ({"rounds": True}, "rounds"),
    ({"show_length_hint": 1}, "show_length_hint"),
    ({"banks": []}, "banks"), ({"banks": ["不存在"]}, "banks"), ({"banks": "默认"}, "banks"),
    ({"nope": 1}, "nope"),
])
def test_invalid_updates(updates, key):
    with pytest.raises(SettingsError) as e:
        validate_settings(specs(), defaults_from(specs()), updates, BANKS)
    assert e.value.key == key


def test_config_defaults_checked_against_ranges():
    with pytest.raises(ConfigError, match="draw_seconds"):
        parse_classic_config({"draw_seconds": 10})
    with pytest.raises(ConfigError, match="reveal_factor"):
        parse_classic_config({"scoring": {"reveal_factor": 1.5}})
    with pytest.raises(ConfigError, match="guesser_min"):
        parse_classic_config({"scoring": {"guesser_min": 200}})
    with pytest.raises(ConfigError, match="bogus"):
        parse_classic_config({"bogus": 1})
    with pytest.raises(ConfigError, match="default_banks"):
        parse_classic_config({"default_banks": "默认"})


def test_scoring_parsed():
    cfg = parse_classic_config({"scoring": {"reveal_factor": 0.5}})
    assert cfg.scoring.reveal_factor == 0.5 and cfg.scoring.guesser_max == 100


def test_unknown_mode_section():
    with pytest.raises(ConfigError, match="nosuch"):
        parse_mode_configs({"nosuch": {}})

import re
from pathlib import Path

import pytest

from server.config import ConfigError, load_config, parse_config

ROOT = Path(__file__).resolve().parents[2]


def test_default_file_loads():
    cfg = load_config(ROOT / "config.toml")
    assert cfg.server.port == 8000 and cfg.room.max_players == 12
    assert len(cfg.drawing.colors) == 7 and cfg.drawing.brush_sizes == (4, 8, 16, 32)
    assert cfg.words_dir == ROOT / "words"
    assert cfg.modes["classic"]["draw_seconds"] == 80


def test_empty_file_equals_defaults(tmp_path):
    cfg = parse_config("", tmp_path)
    assert cfg.room.min_players == 2 and cfg.room.away_after_seconds == 60
    assert cfg.words_dir == tmp_path / "words" and cfg.modes == {}


def test_default_file_matches_dataclass_defaults(tmp_path):
    from_file = load_config(ROOT / "config.toml")
    empty = parse_config("", ROOT)
    assert (from_file.server, from_file.room, from_file.drawing) == (empty.server, empty.room, empty.drawing)


def test_words_dir_relative_to_config_dir(tmp_path):
    assert parse_config('[words]\ndir = "w"', tmp_path).words_dir == tmp_path / "w"


@pytest.mark.parametrize("text, key", [
    ("[room]\nmax_player = 3", "room.max_player"),
    ("[room]\nmax_players = 3\nmin_players = 4", "min_players"),
    ("[room]\nmin_players = 1", "min_players"),
    ("[room]\naway_after_seconds = 0", "away_after_seconds"),
    ("[room]\nmax_players = \"12\"", "max_players"),
    ("[room]\nmax_players = true", "max_players"),
    ('[drawing]\ncolors = ["red"]', "colors"),
    ("[drawing]\nbrush_sizes = []", "brush_sizes"),
    ("[nosuch]\na = 1", "nosuch"),
    ("[modes]\nclassic = 3", "modes.classic"),
])
def test_invalid_config_names_the_key(tmp_path, text, key):
    with pytest.raises(ConfigError, match=re.escape(key)):
        parse_config(text, tmp_path)


def test_invalid_toml_is_config_error(tmp_path):
    with pytest.raises(ConfigError):
        parse_config("[room\n", tmp_path)

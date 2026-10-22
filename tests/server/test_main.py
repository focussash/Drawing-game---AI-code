import pytest

import main
from server.net.lan import lan_ip


def test_bad_config_exits_with_message(tmp_path, capsys):
    bad = tmp_path / "config.toml"
    bad.write_text("[room]\nmax_player = 3\n", encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        main.main(["--config", str(bad)])
    assert e.value.code != 0
    assert "room.max_player" in capsys.readouterr().err


def test_missing_config_exits(tmp_path, capsys):
    with pytest.raises(SystemExit):
        main.main(["--config", str(tmp_path / "nope.toml")])
    assert "nope.toml" in capsys.readouterr().err


def test_lan_ip_returns_str_or_none():
    ip = lan_ip()
    assert ip is None or (isinstance(ip, str) and ip.count(".") == 3)


def test_banner_lists_urls_and_banks(tmp_path, capsys):
    from server.config import parse_config
    (tmp_path / "words").mkdir()
    (tmp_path / "words" / "动物.txt").write_text("猫\n狗\n", encoding="utf-8")
    main._print_banner(parse_config("", tmp_path))
    out = capsys.readouterr().out
    assert "http://localhost:8000" in out and "动物(2)" in out


def test_banner_warns_without_banks(tmp_path, capsys):
    from server.config import parse_config
    main._print_banner(parse_config("", tmp_path))
    assert "没有任何 .txt 词库" in capsys.readouterr().out

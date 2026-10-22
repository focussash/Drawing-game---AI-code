import pytest

from server.players import InvalidNickname, PlayerList, RoomFull, clean_nickname


def test_clean_nickname():
    assert clean_nickname("  小  王 ", 12) == "小 王"
    assert clean_nickname("a" * 20, 12) == "a" * 12
    with pytest.raises(InvalidNickname):
        clean_nickname("   ", 12)


def test_add_dedupes_and_limits():
    pl = PlayerList(max_players=3, max_nickname_length=12)
    a, b, c = pl.add("小王"), pl.add("小王"), pl.add("小王")
    assert (a.nickname, b.nickname, c.nickname) == ("小王", "小王2", "小王3")
    assert len({a.id, b.id, c.id}) == 3 and len({a.token, b.token, c.token}) == 3
    with pytest.raises(RoomFull):
        pl.add("x")
    assert pl.by_token(a.token) is a and pl.get(b.id) is b
    assert pl.ids() == [a.id, b.id, c.id] and len(pl) == 3


def test_unknown_lookups_return_none():
    pl = PlayerList(2, 12)
    assert pl.get("p99") is None and pl.by_token("nope") is None


def test_away_threshold():
    pl = PlayerList(4, 12)
    p = pl.add("a")
    pl.set_offline(p.id, now=100)
    assert not p.online
    assert not pl.is_away(p.id, 159, 60) and pl.is_away(p.id, 160, 60)
    pl.set_online(p.id)
    assert p.online and p.offline_since is None and not pl.is_away(p.id, 1000, 60)


def test_remove_keeps_order():
    pl = PlayerList(4, 12)
    a, b, c = pl.add("a"), pl.add("b"), pl.add("c")
    pl.remove(b.id)
    assert pl.ids() == [a.id, c.id] and [p.id for p in pl.ordered()] == [a.id, c.id]


def test_ids_not_reused_after_remove():
    pl = PlayerList(2, 12)
    a = pl.add("a")
    pl.remove(a.id)
    assert pl.add("b").id != a.id

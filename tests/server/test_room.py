from random import Random

import pytest

from server.audience import Audience
from server.config import parse_config
from server.modes import parse_mode_configs
from server.registry import RoomRegistry
from server.room import JoinError, Room
from tests.server.fakes import FakeClock

WORDS = "长颈鹿\n熊猫\n苹果\n香蕉\n"


def make_config(tmp_path, **room):
    words = tmp_path / "words"
    words.mkdir(parents=True, exist_ok=True)
    (words / "默认.txt").write_text(WORDS, encoding="utf-8")
    lines = "\n".join(f"{k} = {v}" for k, v in room.items())
    return parse_config(f"[room]\n{lines}\n", tmp_path)


def make_room(tmp_path, clock, **room):
    cfg = make_config(tmp_path, **room)
    return Room("ABCD", cfg, parse_mode_configs(cfg.modes), clock, Random(0))


def enter(room, name, token=None):
    p = room.join(token, name)
    room.connect(p.id)
    return p


def of(msgs, pid, type_):
    return [m for a, m in msgs if a.includes(pid) and m["type"] == type_]


def started(tmp_path, n=2, **room):
    clock = FakeClock()
    r = make_room(tmp_path, clock, **room)
    ps = [enter(r, f"玩家{i}") for i in range(1, n + 1)]
    r.handle(ps[0].id, {"type": "start"})
    r.drain_outbox()
    return r, clock, ps


def drawing(tmp_path, n=2):
    r, clock, ps = started(tmp_path, n)
    r.handle(ps[0].id, {"type": "action", "name": "choose", "data": {"index": 0}})
    r.drain_outbox()
    return r, clock, ps


STROKE = {"type": "stroke_begin", "id": 1, "tool": "brush", "color": "#000000", "size": 8, "x": 10, "y": 20}


def test_join_and_welcome(tmp_path):
    r = make_room(tmp_path, FakeClock())
    p = enter(r, "小王")
    msgs = r.drain_outbox()
    first_audience, welcome = msgs[0]
    assert welcome["type"] == "welcome" and first_audience == Audience.of(p.id)
    assert welcome["you"] == p.id and welcome["token"] == p.token
    snap = welcome["snapshot"]
    assert snap["state"] == "lobby" and snap["host"] == p.id and snap["room"] == "ABCD"
    assert snap["lobby"]["banks"] == ["默认"] and snap["lobby"]["values"]["rounds"] == 3
    assert snap["drawing"]["width"] == 1600 and snap["limits"]["max_chat_length"] == 60
    assert snap["game"] is None and snap["canvas"] == [] and snap["chat"] == []
    assert of(msgs, p.id, "players")[-1]["players"] == [{"id": p.id, "nickname": "小王", "online": True, "host": True}]


def test_join_needs_valid_nickname(tmp_path):
    r = make_room(tmp_path, FakeClock())
    for nickname, code in [(None, "need_nickname"), ("  ", "bad_nickname"), (5, "bad_nickname")]:
        with pytest.raises(JoinError) as e:
            r.join(None, nickname)
        assert e.value.code == code


def test_resume_with_token(tmp_path):
    r = make_room(tmp_path, FakeClock())
    p = enter(r, "小王")
    r.disconnect(p.id)
    assert not p.online
    assert r.join(p.token, None) is p
    r.connect(p.id)
    assert p.online


def test_unknown_token_with_nickname_joins_new(tmp_path):
    r = make_room(tmp_path, FakeClock())
    p = r.join("bogus-token", "小王")
    assert p.nickname == "小王" and p.token != "bogus-token"


def test_room_full(tmp_path):
    r = make_room(tmp_path, FakeClock(), max_players=2)
    enter(r, "a")
    enter(r, "b")
    with pytest.raises(JoinError) as e:
        r.join(None, "c")
    assert e.value.code == "room_full"


def test_settings_host_only(tmp_path):
    r = make_room(tmp_path, FakeClock())
    host, p2 = enter(r, "a"), enter(r, "b")
    r.drain_outbox()
    r.handle(p2.id, {"type": "settings", "values": {"rounds": 5}})
    assert of(r.drain_outbox(), p2.id, "error")[0]["code"] == "not_allowed"
    r.handle(host.id, {"type": "settings", "values": {"rounds": 5}})
    assert of(r.drain_outbox(), p2.id, "lobby")[0]["values"]["rounds"] == 5
    r.handle(host.id, {"type": "settings", "values": {"rounds": 0}})
    err = of(r.drain_outbox(), host.id, "error")[0]
    assert err["code"] == "bad_settings" and "rounds" in err["message"]


def test_start_checks(tmp_path):
    r = make_room(tmp_path, FakeClock())
    host = enter(r, "a")
    r.handle(host.id, {"type": "start"})
    assert of(r.drain_outbox(), host.id, "error")[0]["code"] == "not_enough_players"
    (tmp_path / "words" / "空.txt").write_text("# nothing\n", encoding="utf-8")
    enter(r, "b")  # connecting in the lobby rescans the word banks
    r.handle(host.id, {"type": "settings", "values": {"banks": ["空"]}})
    r.handle(host.id, {"type": "start"})
    assert of(r.drain_outbox(), host.id, "error")[-1]["code"] == "no_words"
    assert r.state == "lobby"


def test_start_creates_game(tmp_path):
    clock = FakeClock()
    r = make_room(tmp_path, clock)
    host, p2 = enter(r, "a"), enter(r, "b")
    r.drain_outbox()
    r.handle(host.id, {"type": "start"})
    msgs = r.drain_outbox()
    assert r.state == "game"
    assert of(msgs, p2.id, "game_started") == [{"type": "game_started", "mode": "classic"}]
    assert of(msgs, p2.id, "phase")[-1]["phase"] == "choosing"


def test_settings_rejected_in_game(tmp_path):
    r, clock, (host, p2) = started(tmp_path)
    r.handle(host.id, {"type": "settings", "values": {"rounds": 5}})
    assert of(r.drain_outbox(), host.id, "error")[0]["code"] == "not_allowed"


def test_kick(tmp_path):
    r = make_room(tmp_path, FakeClock())
    host, p2 = enter(r, "a"), enter(r, "b")
    r.drain_outbox()
    r.handle(host.id, {"type": "kick", "player_id": p2.id})
    msgs = r.drain_outbox()
    assert of(msgs, p2.id, "kicked") == [{"type": "kicked"}]
    assert r.drain_closes() == [p2.id] and r.drain_closes() == []
    assert r.players.get(p2.id) is None
    with pytest.raises(JoinError) as e:
        r.join(p2.token, "x")
    assert e.value.code == "banned"
    r.handle(host.id, {"type": "kick", "player_id": host.id})
    assert of(r.drain_outbox(), host.id, "error")[0]["code"] == "not_allowed"


def test_kick_during_game_notifies_mode(tmp_path):
    r, clock, (host, p2, p3) = drawing(tmp_path, n=3)
    r.handle(host.id, {"type": "kick", "player_id": p3.id})
    r.handle(p2.id, {"type": "chat", "text": r.mode.word})
    assert of(r.drain_outbox(), host.id, "turn_result")[-1]["reason"] == "all_correct"


def test_host_transfers_when_away(tmp_path):
    clock = FakeClock()
    r = make_room(tmp_path, clock)
    host, p2, p3 = enter(r, "a"), enter(r, "b"), enter(r, "c")
    r.disconnect(host.id)
    clock.advance(59)
    r.tick()
    assert r.host_id == host.id
    clock.advance(1)
    r.tick()
    assert r.host_id == p2.id
    players = of(r.drain_outbox(), p3.id, "players")[-1]["players"]
    assert [p["host"] for p in players if p["id"] == p2.id] == [True]


def test_lobby_drops_away_players_game_keeps_them(tmp_path):
    clock = FakeClock()
    r = make_room(tmp_path, clock)
    enter(r, "a")
    p2 = enter(r, "b")
    r.disconnect(p2.id)
    clock.advance(60)
    r.tick()
    assert r.players.get(p2.id) is None

    r2, clock2, (h, q2, q3) = started(tmp_path / "g", n=3)
    r2.disconnect(q3.id)
    clock2.advance(60)
    r2.tick()
    assert r2.players.get(q3.id) is not None


def test_stroke_relay_only_from_drawer(tmp_path):
    r, clock, (host, p2) = drawing(tmp_path)
    r.handle(host.id, STROKE)
    r.handle(host.id, {"type": "stroke_points", "id": 1, "pts": [30, 40]})
    msgs = r.drain_outbox()
    assert of(msgs, p2.id, "stroke_begin")[0]["x"] == 10 and of(msgs, host.id, "stroke_begin") == []
    assert of(msgs, p2.id, "stroke_points")[0]["pts"] == [30, 40]
    assert r.snapshot_for(p2.id)["canvas"][0]["pts"] == [10, 20, 30, 40]
    r.handle(p2.id, STROKE)
    assert of(r.drain_outbox(), p2.id, "error")[0]["code"] == "not_allowed"
    r.handle(host.id, {**STROKE, "id": 2, "color": "#123456"})
    assert of(r.drain_outbox(), host.id, "error")[0]["code"] == "bad_message"


def test_eraser_uses_eraser_color_and_sizes(tmp_path):
    r, clock, (host, p2) = drawing(tmp_path)
    r.handle(host.id, {**STROKE, "tool": "eraser", "color": "#000000", "size": 32})
    assert of(r.drain_outbox(), p2.id, "stroke_begin")[0]["color"] == "#ffffff"
    r.handle(host.id, {**STROKE, "id": 2, "tool": "eraser", "size": 8})
    assert of(r.drain_outbox(), host.id, "error")[0]["code"] == "bad_message"


def test_canvas_clear_by_drawer(tmp_path):
    r, clock, (host, p2) = drawing(tmp_path)
    r.handle(host.id, STROKE)
    r.handle(host.id, {"type": "canvas_clear"})
    assert of(r.drain_outbox(), p2.id, "canvas_clear")
    assert r.snapshot_for(p2.id)["canvas"] == []


@pytest.mark.parametrize("msg", [
    {}, {"type": 5}, {"type": "chat"}, {"type": "chat", "text": "x" * 1000}, {"type": "settings", "values": []},
    {"type": "kick"}, {"type": "kick", "player_id": "p99"}, {"type": "stroke_points", "id": 1, "pts": [1]},
    {"type": "action", "name": "choose", "data": "x"}, {"type": "action"}, {"type": "nosuch"},
    {"type": "stroke_begin", "id": 1, "tool": "brush", "color": "#000000", "size": 8, "x": 99999, "y": 0},
    {"type": "stroke_begin", "id": 1, "tool": "pen", "color": "#000000", "size": 8, "x": 0, "y": 0},
    {"type": "stroke_points", "id": 1, "pts": [0, 1300]}, ["not", "a", "dict"],
])
def test_malformed_messages_never_raise(tmp_path, msg):
    r = make_room(tmp_path / "lobby", FakeClock())
    host = enter(r, "a")
    enter(r, "b")
    r.drain_outbox()
    r.handle(host.id, msg)
    assert of(r.drain_outbox(), host.id, "error")

    g, clock, (gh, g2) = drawing(tmp_path / "game")
    g.handle(gh.id, msg)
    assert of(g.drain_outbox(), gh.id, "error")


def test_lobby_chat_public(tmp_path):
    r = make_room(tmp_path, FakeClock())
    a, b = enter(r, "a"), enter(r, "b")
    r.drain_outbox()
    r.handle(a.id, {"type": "chat", "text": " 你好 "})
    entry = of(r.drain_outbox(), b.id, "chat")[0]["entry"]
    assert entry == {"from": a.id, "nickname": "a", "text": "你好", "kind": "chat", "private": False}
    assert r.snapshot_for(b.id)["chat"] == [entry]


def test_game_over_returns_to_lobby(tmp_path):
    clock = FakeClock()
    r = make_room(tmp_path, clock)
    host, p2 = enter(r, "a"), enter(r, "b")
    r.handle(host.id, {"type": "settings", "values": {"rounds": 1}})
    r.handle(host.id, {"type": "start"})
    for seconds in (15, 80, 6, 15, 80, 6):
        clock.advance(seconds)
        r.tick()
    msgs = r.drain_outbox()
    assert r.state == "lobby"
    results = of(msgs, p2.id, "game_over")[0]["results"]
    assert {(x["id"], x["nickname"], x["score"]) for x in results} == {(host.id, "a", 0), (p2.id, "b", 0)}
    assert of(msgs, p2.id, "lobby")[-1]["last_results"] == results
    assert r.snapshot_for(p2.id)["game"] is None


def test_abandoned_after_ttl(tmp_path):
    clock = FakeClock()
    r = make_room(tmp_path, clock)
    p = enter(r, "a")
    r.disconnect(p.id)
    clock.advance(599)
    assert not r.is_abandoned()
    clock.advance(1)
    assert r.is_abandoned()


def test_never_joined_room_is_abandoned(tmp_path):
    clock = FakeClock()
    r = make_room(tmp_path, clock)
    clock.advance(600)
    assert r.is_abandoned()


def test_late_join_gets_game_snapshot(tmp_path):
    r, clock, (host, p2) = drawing(tmp_path)
    r.handle(host.id, STROKE)
    r.drain_outbox()  # the network layer flushes after every call, so nothing is pending at connect
    p3 = enter(r, "c")
    msgs = r.drain_outbox()
    welcome = of(msgs, p3.id, "welcome")[0]
    assert welcome["snapshot"]["game"]["phase"] == "drawing"
    assert len(welcome["snapshot"]["canvas"]) == 1
    assert p3.id in welcome["snapshot"]["game"]["scores"]
    assert [m["type"] for a, m in msgs if a.includes(p3.id)][0] == "welcome"


def test_next_deadline_covers_mode_and_away(tmp_path):
    r, clock, (host, p2) = started(tmp_path)
    assert r.next_deadline() == clock.now() + 15
    r.disconnect(p2.id)
    clock.advance(1)
    assert r.next_deadline() == clock.now() + 14


def test_registry_codes_unique(tmp_path):
    cfg = make_config(tmp_path)
    reg = RoomRegistry(cfg, FakeClock(), Random(0))
    codes = {reg.create().code for _ in range(50)}
    assert len(codes) == 50 and all(len(c) == 4 for c in codes)
    code = next(iter(codes))
    assert reg.get(code).code == code
    reg.remove(code)
    assert reg.get(code) is None

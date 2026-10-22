from random import Random

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from server.config import parse_config
from server.net.app import create_app


@pytest.fixture
def client(tmp_path):
    (tmp_path / "words").mkdir()
    (tmp_path / "words" / "默认.txt").write_text("长颈鹿\n熊猫\n苹果\n", encoding="utf-8")
    app = create_app(parse_config("", tmp_path), rng=Random(0))
    with TestClient(app) as c:
        c.app_state = app.state
        yield c


def new_room(client):
    return client.post("/api/rooms").json()["code"]


def hello(ws, **kw):
    ws.send_json({"type": "hello", **kw})
    msg = ws.receive_json()
    assert msg["type"] == "welcome", msg
    return msg


def recv_until(ws, type_, limit=50):
    for _ in range(limit):
        msg = ws.receive_json()
        if msg["type"] == type_:
            return msg
    raise AssertionError(f"no {type_} message")


def close_code(ws, limit=50):
    with pytest.raises(WebSocketDisconnect) as e:
        for _ in range(limit):
            ws.receive_json()
    return e.value.code


def test_pages_and_room_creation(client):
    assert client.get("/").status_code == 200 and "你画我猜" in client.get("/").text
    assert client.get("/r/ABCD").status_code == 200
    code = new_room(client)
    assert len(code) == 4 and code.isupper()


def test_hello_welcome_and_players(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}") as ws:
        welcome = hello(ws, nickname="小王")
        assert welcome["you"] and welcome["snapshot"]["room"] == code
        players = ws.receive_json()
        assert players["type"] == "players" and len(players["players"]) == 1


def test_lowercase_room_code_accepted(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code.lower()}") as ws:
        hello(ws, nickname="小王")


def test_unknown_room_closes_4004(client):
    with client.websocket_connect("/ws/ZZZZ") as ws:
        assert ws.receive_json()["code"] == "room_not_found"
        assert close_code(ws) == 4004


def test_first_message_must_be_hello(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}") as ws:
        ws.send_json({"type": "chat", "text": "hi"})
        assert ws.receive_json()["code"] == "bad_message"
        assert close_code(ws) == 4000


def test_join_error_closes_4000(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}") as ws:
        ws.send_json({"type": "hello"})
        assert ws.receive_json()["code"] == "need_nickname"
        assert close_code(ws) == 4000


def test_ping_pong(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}") as ws:
        hello(ws, nickname="a")
        ws.send_json({"type": "ping"})
        assert recv_until(ws, "pong") == {"type": "pong"}


def test_invalid_json_ignored(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}") as ws:
        hello(ws, nickname="a")
        ws.send_text("{not json")
        ws.send_json({"type": "ping"})
        assert recv_until(ws, "pong")


def test_resume_replaces_old_connection(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}") as ws1:
        first = hello(ws1, nickname="a")
        with client.websocket_connect(f"/ws/{code}") as ws2:
            second = hello(ws2, token=first["token"])
            assert second["you"] == first["you"]
            assert close_code(ws1) == 4001


def test_stale_close_does_not_mark_offline(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}") as ws2:
        with client.websocket_connect(f"/ws/{code}") as ws1:
            first = hello(ws1, nickname="a")
            hello(ws2, token=first["token"])
            assert close_code(ws1) == 4001
        # ws1 is fully closed now; the player must still be online via ws2
        ws2.send_json({"type": "ping"})
        recv_until(ws2, "pong")
        room = client.app_state.registry.get(code)
        assert room.players.get(first["you"]).online


def test_chat_roundtrip_two_clients(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}") as a, client.websocket_connect(f"/ws/{code}") as b:
        hello(a, nickname="a")
        hello(b, nickname="b")
        a.send_json({"type": "chat", "text": "你好"})
        assert recv_until(b, "chat")["entry"]["text"] == "你好"


def test_kick_closes_4003(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}") as a, client.websocket_connect(f"/ws/{code}") as b:
        hello(a, nickname="a")
        you_b = hello(b, nickname="b")["you"]
        a.send_json({"type": "kick", "player_id": you_b})
        assert recv_until(b, "kicked") == {"type": "kicked"}
        assert close_code(b) == 4003


def test_one_turn_over_websocket(client):
    code = new_room(client)
    with client.websocket_connect(f"/ws/{code}") as a, client.websocket_connect(f"/ws/{code}") as b:
        hello(a, nickname="a")
        hello(b, nickname="b")
        a.send_json({"type": "settings", "values": {"word_choices": 1}})
        a.send_json({"type": "start"})
        recv_until(a, "choices")
        a.send_json({"type": "action", "name": "choose", "data": {"index": 0}})
        word = recv_until(a, "word")["word"]
        b.send_json({"type": "chat", "text": word})
        assert recv_until(b, "turn_result")["reason"] == "all_correct"
        assert recv_until(a, "turn_result")["reason"] == "all_correct"

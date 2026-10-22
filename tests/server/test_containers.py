from server.audience import Audience
from server.canvas_log import CanvasLog
from server.chatlog import ChatLog


def test_audience():
    assert Audience.everyone().includes("p1")
    assert not Audience.of("p1").includes("p2") and Audience.of("p1", "p2").includes("p2")
    e = Audience.all_except("p1")
    assert not e.includes("p1") and e.includes("p2")


def test_chatlog_visibility_and_limit():
    log = ChatLog(limit=2)
    log.append(Audience.everyone(), {"t": 1})
    log.append(Audience.of("p1"), {"t": 2})
    log.append(Audience.everyone(), {"t": 3})
    assert log.visible_to("p2") == [{"t": 3}]
    assert log.visible_to("p1") == [{"t": 2}, {"t": 3}]
    log.clear()
    assert log.visible_to("p1") == []


def test_canvas_log_roundtrip():
    c = CanvasLog()
    c.begin(1, "brush", "#000000", 8, 10, 20)
    assert c.extend(1, [30, 40, 50, 60]) and not c.extend(99, [1, 2])
    assert c.snapshot() == [{"tool": "brush", "color": "#000000", "size": 8, "pts": [10, 20, 30, 40, 50, 60]}]
    c.clear()
    assert c.snapshot() == []


def test_canvas_log_point_budget():
    c = CanvasLog(max_points=6)
    c.begin(1, "brush", "#000000", 8, 0, 0)
    assert c.extend(1, [1, 1, 2, 2]) and not c.extend(1, [3, 3])


def test_canvas_snapshot_is_a_copy():
    c = CanvasLog()
    c.begin(1, "brush", "#000000", 8, 0, 0)
    c.snapshot()[0]["pts"].append(99)
    assert c.snapshot()[0]["pts"] == [0, 0]

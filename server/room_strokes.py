"""Validation of drawing messages against the palette, brush sizes and canvas bounds."""

from __future__ import annotations

from server.canvas_log import CANVAS_HEIGHT, CANVAS_WIDTH, ERASER_COLOR
from server.config import DrawingConfig
from server.msgparse import BadMessage, req_int, req_int_list, req_str
from server.protocol_limits import MAX_POINTS_PER_MESSAGE

MAX_STROKE_ID = 2**31 - 1


def parse_stroke_begin(msg: dict, drawing: DrawingConfig) -> dict:
    tool = msg.get("tool")
    if tool == "brush":
        color = req_str(msg, "color", 7)
        if color not in drawing.colors:
            raise BadMessage("color")
        sizes = drawing.brush_sizes
    elif tool == "eraser":
        color = ERASER_COLOR
        sizes = drawing.eraser_sizes
    else:
        raise BadMessage("tool")
    size = req_int(msg, "size", 1, max(sizes))
    if size not in sizes:
        raise BadMessage("size")
    return {
        "id": req_int(msg, "id", 0, MAX_STROKE_ID),
        "tool": tool,
        "color": color,
        "size": size,
        "x": req_int(msg, "x", 0, CANVAS_WIDTH),
        "y": req_int(msg, "y", 0, CANVAS_HEIGHT),
    }


def parse_stroke_points(msg: dict) -> tuple[int, list[int]]:
    stroke_id = req_int(msg, "id", 0, MAX_STROKE_ID)
    pts = req_int_list(msg, "pts", MAX_POINTS_PER_MESSAGE, 0, max(CANVAS_WIDTH, CANVAS_HEIGHT))
    if len(pts) % 2 or any(x > CANVAS_WIDTH for x in pts[0::2]) or any(y > CANVAS_HEIGHT for y in pts[1::2]):
        raise BadMessage("pts")
    return stroke_id, pts

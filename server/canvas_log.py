"""Strokes of the current drawing, kept so (re)joining players see the whole picture."""

from __future__ import annotations

CANVAS_WIDTH = 1600
CANVAS_HEIGHT = 1200
MAX_POINTS_PER_DRAWING = 100_000  # total flat coordinates across all strokes
ERASER_COLOR = "#ffffff"


class CanvasLog:
    def __init__(self, max_points: int = MAX_POINTS_PER_DRAWING):
        self._max_points = max_points
        self._strokes: dict[int, dict] = {}
        self._points = 0

    def begin(self, stroke_id: int, tool: str, color: str, size: int, x: int, y: int) -> bool:
        if self._points + 2 > self._max_points:
            return False
        self._strokes[stroke_id] = {"tool": tool, "color": color, "size": size, "pts": [x, y]}
        self._points += 2
        return True

    def extend(self, stroke_id: int, pts: list[int]) -> bool:
        stroke = self._strokes.get(stroke_id)
        if stroke is None or self._points + len(pts) > self._max_points:
            return False
        stroke["pts"].extend(pts)
        self._points += len(pts)
        return True

    def clear(self) -> None:
        self._strokes.clear()
        self._points = 0

    def snapshot(self) -> list[dict]:
        return [{**s, "pts": list(s["pts"])} for s in self._strokes.values()]

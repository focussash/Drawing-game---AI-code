"""Adapter giving a game mode the ModeContext view of its room."""

from __future__ import annotations

from typing import TYPE_CHECKING

from server.audience import Audience
from server.config import RoomConfig

if TYPE_CHECKING:
    from server.room import Room


class RoomModeContext:
    def __init__(self, room: Room):
        self._room = room

    def player_ids(self) -> list[str]:
        return self._room.players.ids()

    def is_online(self, pid: str) -> bool:
        p = self._room.players.get(pid)
        return p is not None and p.online

    def is_away(self, pid: str) -> bool:
        room = self._room
        return room.players.is_away(pid, room.clock.now(), room.config.room.away_after_seconds)

    def is_host(self, pid: str) -> bool:
        return pid == self._room.host_id

    def nickname(self, pid: str) -> str:
        p = self._room.players.get(pid)
        return p.nickname if p else ""

    def send(self, audience: Audience, msg: dict) -> None:
        self._room.send(audience, msg)

    def post_chat(self, audience: Audience, entry: dict) -> None:
        self._room.post_chat(audience, entry)

    def clear_canvas(self) -> None:
        self._room.clear_canvas()

    def room_config(self) -> RoomConfig:
        return self._room.config.room

    def finish(self, results: list[dict]) -> None:
        self._room.finish_game(results)

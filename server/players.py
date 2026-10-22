"""Players in a room: identity tokens, nicknames, online state, join order."""

from __future__ import annotations

import secrets
from dataclasses import dataclass


class RoomFull(Exception):
    pass


class InvalidNickname(Exception):
    pass


def clean_nickname(raw: str, max_len: int) -> str:
    name = " ".join(str(raw).split())[:max_len]
    if not name:
        raise InvalidNickname(raw)
    return name


@dataclass
class Player:
    id: str
    token: str
    nickname: str
    seq: int
    online: bool = True
    offline_since: float | None = None


class PlayerList:
    def __init__(self, max_players: int, max_nickname_length: int):
        self._max_players = max_players
        self._max_nickname_length = max_nickname_length
        self._players: dict[str, Player] = {}  # insertion order = join order
        self._seq = 0

    def add(self, nickname: str) -> Player:
        if len(self._players) >= self._max_players:
            raise RoomFull()
        name = self._unique(clean_nickname(nickname, self._max_nickname_length))
        self._seq += 1
        player = Player(id=f"p{self._seq}", token=secrets.token_urlsafe(16), nickname=name, seq=self._seq)
        self._players[player.id] = player
        return player

    def _unique(self, name: str) -> str:
        taken = {p.nickname for p in self._players.values()}
        if name not in taken:
            return name
        n = 2
        while True:
            suffix = str(n)
            candidate = name[: self._max_nickname_length - len(suffix)] + suffix
            if candidate not in taken:
                return candidate
            n += 1

    def get(self, pid: str) -> Player | None:
        return self._players.get(pid)

    def by_token(self, token: str) -> Player | None:
        return next((p for p in self._players.values() if p.token == token), None)

    def remove(self, pid: str) -> None:
        self._players.pop(pid, None)

    def ordered(self) -> list[Player]:
        return list(self._players.values())

    def ids(self) -> list[str]:
        return list(self._players)

    def set_online(self, pid: str) -> None:
        p = self._players[pid]
        p.online = True
        p.offline_since = None

    def set_offline(self, pid: str, now: float) -> None:
        p = self._players[pid]
        p.online = False
        p.offline_since = now

    def is_away(self, pid: str, now: float, away_after: float) -> bool:
        p = self._players.get(pid)
        if p is None:
            return True
        return not p.online and p.offline_since is not None and now - p.offline_since >= away_after

    def __len__(self) -> int:
        return len(self._players)

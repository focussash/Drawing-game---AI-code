"""Creates rooms with short unique codes and finds them again."""

from __future__ import annotations

import random

from server.clock import Clock
from server.config import AppConfig
from server.modes import parse_mode_configs
from server.room import Room

CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # no I/L/O/0/1: easy to read aloud
CODE_LENGTH = 4


class RoomRegistry:
    def __init__(self, config: AppConfig, clock: Clock, rng: random.Random):
        self.config = config
        self.clock = clock
        self._rng = rng
        self.mode_configs = parse_mode_configs(config.modes)
        self._rooms: dict[str, Room] = {}

    def create(self) -> Room:
        code = self._new_code()
        room = Room(code, self.config, self.mode_configs, self.clock, random.Random(self._rng.getrandbits(64)))
        self._rooms[code] = room
        return room

    def get(self, code: str) -> Room | None:
        return self._rooms.get(code)

    def remove(self, code: str) -> None:
        self._rooms.pop(code, None)

    def _new_code(self) -> str:
        while True:
            code = "".join(self._rng.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))
            if code not in self._rooms:
                return code

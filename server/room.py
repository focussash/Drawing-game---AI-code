"""A room: players, host, lobby settings, and dispatch into the running game mode.

Pure logic: no network and no real clock. The network layer calls join/connect/
disconnect/handle/tick and sends whatever drain_outbox() returns.
"""

from __future__ import annotations

import logging
import random
from typing import Any

from server.audience import Audience
from server.canvas_log import CANVAS_HEIGHT, CANVAS_WIDTH, CanvasLog
from server.chatlog import ChatLog
from server.clock import Clock
from server.config import AppConfig
from server.modes import MODES
from server.modes.base import Mode, SettingsError
from server.msgparse import BadMessage, req_dict, req_str
from server.players import InvalidNickname, Player, PlayerList, RoomFull
from server.room_context import RoomModeContext
from server.room_lobby import LobbyState
from server.room_strokes import parse_stroke_begin, parse_stroke_points
from server.wordbank import UnknownBank, WordPool, load_banks

log = logging.getLogger(__name__)

LOBBY, GAME = "lobby", "game"
DEFAULT_MODE = "classic"


class _Handled(Exception):
    """Internal: the error was already reported to the sender; stop handling."""


class JoinError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class Room:
    def __init__(self, code: str, config: AppConfig, mode_configs: dict[str, Any], clock: Clock,
                 rng: random.Random, mode_name: str = DEFAULT_MODE):
        self.code = code
        self.config = config
        self.clock = clock
        self.rng = rng
        self.mode_name = mode_name
        self._mode_cls: type[Mode] = MODES[mode_name]
        self._mode_cfg = mode_configs[mode_name]

        room_cfg = config.room
        self.players = PlayerList(room_cfg.max_players, room_cfg.max_nickname_length)
        self.host_id: str | None = None
        self.state = LOBBY
        self.lobby = LobbyState(lambda banks: self._mode_cls.setting_specs(self._mode_cfg, banks), config.words_dir)
        self.chat = ChatLog(room_cfg.chat_history)
        self.canvas = CanvasLog()
        self.mode: Mode | None = None

        self._in_game: set[str] = set()  # players the mode has been told about
        self._banned: set[str] = set()
        self._outbox: list[tuple[Audience, dict]] = []
        self._closes: list[str] = []
        self._empty_since: float | None = clock.now()
        self._handlers = {
            "chat": self._on_chat, "settings": self._on_settings, "start": self._on_start,
            "kick": self._on_kick, "stroke_begin": self._on_stroke_begin,
            "stroke_points": self._on_stroke_points, "canvas_clear": self._on_canvas_clear,
            "action": self._on_action,
        }

    # ---- connection lifecycle -------------------------------------------

    def join(self, token: str | None, nickname: Any) -> Player:
        if token:
            if token in self._banned:
                raise JoinError("banned")
            existing = self.players.by_token(token)
            if existing is not None:
                return existing
        if nickname is None:
            raise JoinError("need_nickname")
        if not isinstance(nickname, str):
            raise JoinError("bad_nickname")
        try:
            player = self.players.add(nickname)
        except RoomFull:
            raise JoinError("room_full") from None
        except InvalidNickname:
            raise JoinError("bad_nickname") from None
        if self.host_id is None:
            self.host_id = player.id
        return player

    def connect(self, pid: str) -> None:
        player = self.players.get(pid)
        if player is None:
            return
        now = self.clock.now()
        self.players.set_online(pid)
        self._empty_since = None
        mark = len(self._outbox)
        if self.state == LOBBY:
            self.lobby.refresh_banks()
        elif self.mode is not None:
            if pid in self._in_game:
                self.mode.on_player_online(pid, now)
            else:
                self._in_game.add(pid)
                self.mode.on_player_joined(pid, now)
        # The welcome goes first so the client never sees a message before its snapshot.
        welcome = {"type": "welcome", "you": pid, "token": player.token, "snapshot": self.snapshot_for(pid)}
        self._outbox.insert(mark, (Audience.of(pid), welcome))
        self._broadcast_players()

    def disconnect(self, pid: str) -> None:
        if self.players.get(pid) is None:
            return
        now = self.clock.now()
        self.players.set_offline(pid, now)
        if self.mode is not None and pid in self._in_game:
            self.mode.on_player_offline(pid, now)
        if not any(p.online for p in self.players.ordered()):
            self._empty_since = now
        self._broadcast_players()

    def handle(self, pid: str, msg: Any) -> None:
        if self.players.get(pid) is None:
            return
        try:
            if not isinstance(msg, dict) or not isinstance(msg.get("type"), str):
                raise BadMessage("type")
            handler = self._handlers.get(msg["type"])
            if handler is None:
                raise BadMessage("type")
            handler(pid, msg)
        except _Handled:
            pass
        except BadMessage:
            self._error(pid, "bad_message", "消息格式不正确")
        except Exception:
            log.exception("room %s: error handling %r from %s", self.code, msg, pid)
            self._error(pid, "bad_message", "服务器处理出错")

    def tick(self) -> None:
        now = self.clock.now()
        away_after = self.config.room.away_after_seconds
        if self.state == LOBBY:
            self._remove_away_players(now)
        if self.host_id is None or self.players.is_away(self.host_id, now, away_after):
            self._transfer_host()
        if self.mode is not None:
            self.mode.on_tick(now)

    def next_deadline(self) -> float | None:
        now = self.clock.now()
        away_after = self.config.room.away_after_seconds
        candidates = [p.offline_since + away_after for p in self.players.ordered()
                      if not p.online and p.offline_since is not None and p.offline_since + away_after > now]
        if self._empty_since is not None:
            candidates.append(self._empty_since + self.config.room.empty_room_ttl_seconds)
        if self.mode is not None and (d := self.mode.next_deadline()) is not None:
            candidates.append(d)
        return min(candidates) if candidates else None

    def is_abandoned(self) -> bool:
        if self._empty_since is None:
            return False
        return self.clock.now() - self._empty_since >= self.config.room.empty_room_ttl_seconds

    def drain_outbox(self) -> list[tuple[Audience, dict]]:
        out, self._outbox = self._outbox, []
        return out

    def drain_closes(self) -> list[str]:
        out, self._closes = self._closes, []
        return out

    # ---- used by RoomModeContext -----------------------------------------

    def send(self, audience: Audience, msg: dict) -> None:
        self._outbox.append((audience, msg))

    def post_chat(self, audience: Audience, entry: dict) -> None:
        self.chat.append(audience, entry)
        self.send(audience, {"type": "chat", "entry": entry})

    def clear_canvas(self) -> None:
        self.canvas.clear()
        self.send(Audience.everyone(), {"type": "canvas_clear"})

    def finish_game(self, results: list[dict]) -> None:
        named = [{"id": r["id"], "nickname": self._nickname(r["id"]), "score": r["score"]} for r in results]
        self.lobby.last_results = named
        self.state = LOBBY
        self.mode = None
        self._in_game.clear()
        self.canvas.clear()
        self.send(Audience.everyone(), {"type": "game_over", "results": named})
        self._remove_away_players(self.clock.now())
        self.lobby.refresh_banks()
        self.send(Audience.everyone(), self.lobby.message())
        self._broadcast_players()

    # ---- snapshot ---------------------------------------------------------

    def snapshot_for(self, pid: str) -> dict:
        lobby = self.lobby.message()
        del lobby["type"]
        drawing = self.config.drawing
        room_cfg = self.config.room
        return {
            "room": self.code, "state": self.state, "mode": self.mode_name, "host": self.host_id,
            "players": self._players_json(), "lobby": lobby,
            "drawing": {"width": CANVAS_WIDTH, "height": CANVAS_HEIGHT, "colors": list(drawing.colors),
                        "brush_sizes": list(drawing.brush_sizes), "eraser_sizes": list(drawing.eraser_sizes)},
            "limits": {"max_chat_length": room_cfg.max_chat_length,
                       "max_nickname_length": room_cfg.max_nickname_length},
            "chat": self.chat.visible_to(pid), "canvas": self.canvas.snapshot(),
            "game": self.mode.snapshot_for(pid, self.clock.now()) if self.mode is not None else None,
        }

    # ---- message handlers -------------------------------------------------

    def _on_chat(self, pid: str, msg: dict) -> None:
        text = req_str(msg, "text", self.config.room.max_chat_length).strip()
        if self.mode is not None:
            self.mode.on_chat(pid, text, self.clock.now())
        else:
            self.post_chat(Audience.everyone(), {"from": pid, "nickname": self._nickname(pid), "text": text,
                                                 "kind": "chat", "private": False})

    def _on_settings(self, pid: str, msg: dict) -> None:
        if pid != self.host_id or self.state != LOBBY:
            return self._error(pid, "not_allowed", "只有房主能在等待界面修改设置")
        values = req_dict(msg, "values")
        try:
            self.lobby.update(values)
        except SettingsError as e:
            return self._error(pid, "bad_settings", str(e))
        self.send(Audience.everyone(), self.lobby.message())

    def _on_start(self, pid: str, msg: dict) -> None:
        if pid != self.host_id or self.state != LOBBY:
            return self._error(pid, "not_allowed", "只有房主能开始游戏")
        online = [p for p in self.players.ordered() if p.online]
        if len(online) < self.config.room.min_players:
            return self._error(pid, "not_enough_players", f"至少需要 {self.config.room.min_players} 人在线")
        self.lobby.refresh_banks()
        try:
            words = load_banks(self.config.words_dir, self.lobby.values.get("banks", []))
        except UnknownBank:
            words = []
        if not words:
            return self._error(pid, "no_words", "选中的词库里没有词")

        now = self.clock.now()
        self.state = GAME
        self._in_game = set(self.players.ids())
        self.canvas.clear()
        self.mode = self._mode_cls(RoomModeContext(self), dict(self.lobby.values), self._mode_cfg,
                                   WordPool(words, self.rng), self.rng)
        self.send(Audience.everyone(), {"type": "game_started", "mode": self.mode_name})
        self.mode.start(now)

    def _on_kick(self, pid: str, msg: dict) -> None:
        target = req_str(msg, "player_id", 32)
        player = self.players.get(target)
        if player is None:
            raise BadMessage("player_id")
        if pid != self.host_id or target == pid:
            return self._error(pid, "not_allowed", "只有房主能移出其他人")
        self.send(Audience.of(target), {"type": "kicked"})
        self._closes.append(target)
        self._banned.add(player.token)
        self._remove_player(target)
        self._broadcast_players()

    def _on_stroke_begin(self, pid: str, msg: dict) -> None:
        self._require_drawer(pid)
        stroke = parse_stroke_begin(msg, self.config.drawing)
        if self.canvas.begin(stroke["id"], stroke["tool"], stroke["color"], stroke["size"], stroke["x"], stroke["y"]):
            self.send(Audience.all_except(pid), {"type": "stroke_begin", **stroke})

    def _on_stroke_points(self, pid: str, msg: dict) -> None:
        self._require_drawer(pid)
        stroke_id, pts = parse_stroke_points(msg)
        if self.canvas.extend(stroke_id, pts):
            self.send(Audience.all_except(pid), {"type": "stroke_points", "id": stroke_id, "pts": pts})

    def _on_canvas_clear(self, pid: str, msg: dict) -> None:
        self._require_drawer(pid)
        self.canvas.clear()
        self.send(Audience.all_except(pid), {"type": "canvas_clear"})

    def _on_action(self, pid: str, msg: dict) -> None:
        name = req_str(msg, "name", 32)
        data = req_dict(msg, "data")
        if self.mode is None:
            return self._error(pid, "not_allowed", "游戏还没开始")
        self.mode.on_action(pid, name, data, self.clock.now())

    # ---- helpers ----------------------------------------------------------

    def _require_drawer(self, pid: str) -> None:
        if self.mode is None or not self.mode.can_draw(pid):
            self._error(pid, "not_allowed", "现在不是你画")
            raise _Handled()

    def _remove_player(self, pid: str) -> None:
        self.players.remove(pid)
        if self.mode is not None and pid in self._in_game:
            self._in_game.discard(pid)
            self.mode.on_player_removed(pid, self.clock.now())
        if pid == self.host_id:
            self._transfer_host()

    def _remove_away_players(self, now: float) -> None:
        away_after = self.config.room.away_after_seconds
        gone = [p.id for p in self.players.ordered() if self.players.is_away(p.id, now, away_after)]
        for pid in gone:
            self._remove_player(pid)
        if gone:
            self._broadcast_players()

    def _transfer_host(self) -> None:
        """Hand the host role to the earliest-joined online player, if any."""
        candidate = next((p.id for p in self.players.ordered() if p.online), None)
        if candidate is None:
            if self.host_id is not None and self.players.get(self.host_id) is None:
                self.host_id = None  # host left and nobody is online; next tick picks one
            return
        if candidate != self.host_id:
            self.host_id = candidate
            self._broadcast_players()

    def _players_json(self) -> list[dict]:
        return [{"id": p.id, "nickname": p.nickname, "online": p.online, "host": p.id == self.host_id}
                for p in self.players.ordered()]

    def _broadcast_players(self) -> None:
        self.send(Audience.everyone(), {"type": "players", "players": self._players_json()})

    def _nickname(self, pid: str) -> str:
        p = self.players.get(pid)
        return p.nickname if p else ""

    def _error(self, pid: str, code: str, message: str) -> None:
        self.send(Audience.of(pid), {"type": "error", "code": code, "message": message})

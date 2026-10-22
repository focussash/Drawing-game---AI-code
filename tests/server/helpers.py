"""Builders for classic-mode tests: a fake room context and a started game."""

from random import Random

from server.config import RoomConfig
from server.modes.base import defaults_from
from server.modes.classic.mode import ClassicMode
from server.modes.classic.settings import classic_setting_specs, parse_classic_config
from server.wordbank import WordPool
from tests.server.fakes import FakeClock


class FakeContext:
    def __init__(self, clock, players, host, room_cfg=None):
        self.clock = clock
        self.players = list(players)
        self.host = host
        self.cfg = room_cfg or RoomConfig()
        self.online = {p: True for p in players}
        self.offline_since: dict[str, float] = {}
        self.sent = []
        self.chats = []
        self.finished = None
        self.canvas_clears = 0

    # ModeContext
    def player_ids(self):
        return list(self.players)

    def is_online(self, pid):
        return pid in self.players and self.online.get(pid, False)

    def is_away(self, pid):
        if pid not in self.players:
            return True
        if self.online.get(pid):
            return False
        return self.clock.now() - self.offline_since[pid] >= self.cfg.away_after_seconds

    def is_host(self, pid):
        return pid == self.host

    def nickname(self, pid):
        return f"N{pid}"

    def send(self, audience, msg):
        self.sent.append((audience, msg))

    def post_chat(self, audience, entry):
        self.chats.append((audience, entry))

    def clear_canvas(self):
        self.canvas_clears += 1

    def room_config(self):
        return self.cfg

    def finish(self, results):
        self.finished = results

    # test controls
    def go_offline(self, pid):
        self.online[pid] = False
        self.offline_since[pid] = self.clock.now()

    def go_online(self, pid):
        self.online[pid] = True
        self.offline_since.pop(pid, None)


def make_game(players=("p1", "p2", "p3"), words=("长颈鹿",), room_cfg=None, **settings):
    clock = FakeClock()
    ctx = FakeContext(clock, players, host=players[0], room_cfg=room_cfg)
    cfg = parse_classic_config({})
    values = defaults_from(classic_setting_specs(cfg, ["默认"]))
    values["word_choices"] = 1
    values.update(settings)
    mode = ClassicMode(ctx, values, cfg, WordPool(list(words), Random(0)), Random(0))
    mode.start(clock.now())
    return mode, ctx, clock


def last(ctx, type_, pid=None):
    for audience, msg in reversed(ctx.sent):
        if msg["type"] == type_ and (pid is None or audience.includes(pid)):
            return msg
    return None


def last_with_audience(ctx, type_):
    for audience, msg in reversed(ctx.sent):
        if msg["type"] == type_:
            return audience, msg
    return None


def last_chat(ctx):
    return ctx.chats[-1] if ctx.chats else (None, None)

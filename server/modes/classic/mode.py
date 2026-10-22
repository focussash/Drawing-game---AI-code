"""Classic 你画我猜: each player draws in turn while the others guess.

Phases per turn: choosing → drawing → turn_end. All timing comes from the
`now` passed in, so the whole game can be driven by a fake clock in tests.
"""

from __future__ import annotations

from typing import Any

from server.audience import Audience
from server.modes.base import Mode, SettingSpec
from server.modes.classic.hints import HintError, WordHint
from server.modes.classic.judge import is_correct
from server.modes.classic.rotation import Rotation
from server.modes.classic.scoring import drawer_points, guesser_points
from server.modes.classic.settings import ClassicConfig, classic_setting_specs, parse_classic_config
from server.modes.classic.turn_timer import TurnTimer
from server.msgparse import BadMessage, req_int
from server.textnorm import mask

CHOOSING, DRAWING, TURN_END, FINISHED = "choosing", "drawing", "turn_end", "finished"


class ClassicMode(Mode):
    name = "classic"

    @classmethod
    def parse_mode_config(cls, raw: dict) -> ClassicConfig:
        return parse_classic_config(raw)

    @classmethod
    def setting_specs(cls, mode_cfg: ClassicConfig, banks: list[str]) -> list[SettingSpec]:
        return classic_setting_specs(mode_cfg, banks)

    def __init__(self, ctx, settings, mode_cfg, words, rng):
        super().__init__(ctx, settings, mode_cfg, words, rng)
        self.rotation = Rotation(settings["rounds"])
        self.timer = TurnTimer()
        self.scores: dict[str, int] = {pid: 0 for pid in ctx.player_ids()}
        self.phase: str | None = None
        self.drawer: str | None = None
        self.choices: list[str] = []
        self.word: str | None = None
        self.hint: WordHint | None = None
        self.correct: list[str] = []
        self.turn_deltas: dict[str, int] = {}
        self.turn_result: dict | None = None
        self.phase_deadline: float | None = None
        self.drawer_offline_since: float | None = None

    # ---- lifecycle -------------------------------------------------------

    def start(self, now: float) -> None:
        self.rotation.start(self.ctx.player_ids())
        self._send_scores()
        self._next_turn(now)

    def _next_turn(self, now: float) -> None:
        present = [p for p in self.ctx.player_ids() if not self.ctx.is_away(p)]
        if len(present) < self.ctx.room_config().min_players:
            return self._finish()
        drawer = self.rotation.next_drawer(self.ctx.player_ids(), self.ctx.is_online)
        choices = self.words.draw(self.settings["word_choices"]) if drawer else []
        if drawer is None or not choices:
            return self._finish()

        self.drawer, self.choices = drawer, choices
        self.word = self.hint = self.turn_result = None
        self.correct, self.turn_deltas = [], {}
        self.drawer_offline_since = None
        self.phase = CHOOSING
        self.phase_deadline = now + self.settings["choose_seconds"]
        self.ctx.clear_canvas()
        self._send_phase(now)
        self.ctx.send(Audience.of(drawer), {"type": "choices", "words": list(choices)})

    def _begin_drawing(self, word: str, now: float) -> None:
        self.words.mark_used(word)
        self.word = word
        self.hint = WordHint(word)
        self.timer.start(now, self.settings["draw_seconds"])
        self.phase = DRAWING
        self.phase_deadline = None
        self._send_phase(now)
        self.ctx.send(Audience.of(self.drawer), {"type": "word", "word": word})

    def _end_turn(self, now: float, reason: str) -> None:
        self.phase = TURN_END
        self.phase_deadline = now + self.settings["reveal_seconds"]
        self.drawer_offline_since = None
        self.turn_result = {"type": "turn_result", "word": self.word, "reason": reason,
                            "drawer": self.drawer, "deltas": dict(self.turn_deltas)}
        self.ctx.send(Audience.everyone(), self.turn_result)
        self._send_phase(now)

    def _finish(self) -> None:
        self.phase = FINISHED
        order = {pid: i for i, pid in enumerate(self.ctx.player_ids())}
        ranked = sorted(self.scores.items(), key=lambda kv: (-kv[1], order.get(kv[0], len(order))))
        self.ctx.finish([{"id": pid, "score": score} for pid, score in ranked])

    # ---- events ----------------------------------------------------------

    def on_tick(self, now: float) -> None:
        if self.phase in (CHOOSING, DRAWING) and self._drawer_gone(now):
            self._end_turn(now, "drawer_left")
        elif self.phase == CHOOSING and now >= self.phase_deadline:
            self._begin_drawing(self.rng.choice(self.choices), now)
        elif self.phase == DRAWING and self.timer.expired(now):
            self._end_turn(now, "time")
        elif self.phase == TURN_END and now >= self.phase_deadline:
            self._next_turn(now)

    def next_deadline(self) -> float | None:
        candidates: list[float] = []
        if self.phase in (CHOOSING, TURN_END):
            candidates.append(self.phase_deadline)
        if self.phase == DRAWING:
            candidates.append(self.timer.deadline)
        if self.phase in (CHOOSING, DRAWING) and self.drawer_offline_since is not None:
            candidates.append(self.drawer_offline_since + self.ctx.room_config().drawer_offline_skip_seconds)
        return min(candidates) if candidates else None

    def on_chat(self, pid: str, text: str, now: float) -> None:
        if self.phase != DRAWING:
            return self._post(Audience.everyone(), pid, text)
        if pid == self.drawer or pid in self.correct:
            return self._post(self._knowers(), pid, text, private=True)
        if is_correct(text, self.word):
            return self._correct_guess(pid, now)
        self._post(Audience.everyone(), pid, text)

    def _correct_guess(self, pid: str, now: float) -> None:
        reveals = self.hint.reveals
        scoring = self.mode_cfg.scoring
        gained = guesser_points(self.timer.remaining(now), self.settings["draw_seconds"], reveals, scoring)
        drawer_gain = drawer_points(reveals, scoring)
        self._add_points(pid, gained)
        self._add_points(self.drawer, drawer_gain)
        self.correct.append(pid)

        self._post(Audience.everyone(), pid, mask(self.word), kind="correct")
        self.ctx.send(Audience.of(pid), {"type": "word", "word": self.word})
        self._send_scores()
        if len(self.correct) == 1 and self.settings["shorten_after_first_correct"]:
            self.timer.shorten_to(now, self.settings["shorten_to_seconds"])
            self._send_timer(now)
        if self._everyone_guessed():
            self._end_turn(now, "all_correct")

    def on_action(self, pid: str, name: str, data: dict, now: float) -> None:
        handler = {"choose": self._act_choose, "reveal": self._act_reveal,
                   "extend": self._act_extend, "skip": self._act_skip}.get(name)
        if handler is None or not isinstance(data, dict):
            return self._error(pid, "bad_message", "无法识别的操作")
        try:
            handler(pid, data, now)
        except BadMessage:
            self._error(pid, "bad_message", "操作参数不正确")

    def _act_choose(self, pid: str, data: dict, now: float) -> None:
        if self.phase != CHOOSING or pid != self.drawer:
            return self._error(pid, "not_allowed", "现在不能选词")
        index = req_int(data, "index", 0, len(self.choices) - 1)
        self._begin_drawing(self.choices[index], now)

    def _act_reveal(self, pid: str, data: dict, now: float) -> None:
        if self.phase != DRAWING or pid != self.drawer:
            return self._error(pid, "not_allowed", "只有画手能揭示字")
        index = req_int(data, "index", 0, len(self.word) - 1)
        try:
            self.hint.reveal(index)
        except HintError as e:
            return self._error(pid, "not_allowed", str(e))
        self.ctx.send(Audience.everyone(), {"type": "hint", "template": self.hint.template(True)})
        self._system("画手揭示了一个字")

    def _act_extend(self, pid: str, data: dict, now: float) -> None:
        if self.phase != DRAWING or pid != self.drawer:
            return self._error(pid, "not_allowed", "只有画手能加时")
        if self._extends_left() <= 0:
            return self._error(pid, "not_allowed", "这一轮加时次数已用完")
        seconds = self.settings["extend_seconds"]
        self.timer.extend(seconds)
        self._send_timer(now)
        self._system(f"画手加时 {seconds} 秒")

    def _act_skip(self, pid: str, data: dict, now: float) -> None:
        if not self.ctx.is_host(pid) or self.phase not in (CHOOSING, DRAWING):
            return self._error(pid, "not_allowed", "只有房主能跳过")
        self._end_turn(now, "skipped")

    # ---- players ---------------------------------------------------------

    def on_player_joined(self, pid: str, now: float) -> None:
        self.scores.setdefault(pid, 0)
        self.rotation.add_late(pid)
        self._send_scores()

    def on_player_offline(self, pid: str, now: float) -> None:
        if pid == self.drawer and self.phase in (CHOOSING, DRAWING):
            self.drawer_offline_since = now
        elif self.phase == DRAWING and self._everyone_guessed():
            self._end_turn(now, "all_correct")

    def on_player_online(self, pid: str, now: float) -> None:
        if pid == self.drawer:
            self.drawer_offline_since = None

    def on_player_removed(self, pid: str, now: float) -> None:
        self.rotation.remove(pid)
        self.scores.pop(pid, None)
        self._send_scores()
        if pid == self.drawer and self.phase in (CHOOSING, DRAWING):
            self._end_turn(now, "drawer_left")
        elif self.phase == DRAWING and self._everyone_guessed():
            self._end_turn(now, "all_correct")

    # ---- queries ---------------------------------------------------------

    def can_draw(self, pid: str) -> bool:
        return self.phase == DRAWING and pid == self.drawer

    def snapshot_for(self, pid: str, now: float) -> dict:
        snap: dict[str, Any] = {
            "phase": self.phase, "round": self.rotation.round, "rounds": self.rotation.rounds,
            "drawer": self.drawer, "remaining_ms": self._remaining_ms(now),
            "template": self._template(), "extends_left": self._extends_left(),
            "scores": dict(self.scores), "correct": list(self.correct),
        }
        if self.phase == CHOOSING and pid == self.drawer:
            snap["choices"] = list(self.choices)
        if self.phase == DRAWING and (pid == self.drawer or pid in self.correct):
            snap["word"] = self.word
        if self.phase == TURN_END:
            snap["word"] = self.word
            snap["turn_result"] = self.turn_result
        return snap

    # ---- helpers ---------------------------------------------------------

    def _everyone_guessed(self) -> bool:
        guessers = [p for p in self.ctx.player_ids() if p != self.drawer and self.ctx.is_online(p)]
        return bool(self.correct) and all(p in self.correct for p in guessers)

    def _drawer_gone(self, now: float) -> bool:
        grace = self.ctx.room_config().drawer_offline_skip_seconds
        return self.drawer_offline_since is not None and now >= self.drawer_offline_since + grace

    def _knowers(self) -> Audience:
        return Audience.of(self.drawer, *self.correct)

    def _extends_left(self) -> int:
        return max(0, self.settings["max_extends_per_turn"] - self.timer.extends_used)

    def _template(self) -> list[str] | None:
        if self.phase != DRAWING:
            return None
        return self.hint.template(self.settings["show_length_hint"])

    def _remaining_ms(self, now: float) -> int:
        if self.phase == DRAWING:
            seconds = self.timer.remaining(now)
        elif self.phase in (CHOOSING, TURN_END):
            seconds = max(0.0, self.phase_deadline - now)
        else:
            seconds = 0.0
        return round(seconds * 1000)

    def _add_points(self, pid: str, points: int) -> None:
        self.scores[pid] = self.scores.get(pid, 0) + points
        self.turn_deltas[pid] = self.turn_deltas.get(pid, 0) + points

    def _send_phase(self, now: float) -> None:
        self.ctx.send(Audience.everyone(), {
            "type": "phase", "phase": self.phase, "round": self.rotation.round, "rounds": self.rotation.rounds,
            "drawer": self.drawer, "remaining_ms": self._remaining_ms(now), "template": self._template(),
            "extends_left": self._extends_left(),
        })

    def _send_timer(self, now: float) -> None:
        self.ctx.send(Audience.everyone(), {"type": "timer", "remaining_ms": self._remaining_ms(now),
                                            "extends_left": self._extends_left()})

    def _send_scores(self) -> None:
        self.ctx.send(Audience.everyone(), {"type": "scores", "scores": dict(self.scores),
                                            "correct": list(self.correct)})

    def _post(self, audience: Audience, pid: str, text: str, kind: str = "chat", private: bool = False) -> None:
        self.ctx.post_chat(audience, {"from": pid, "nickname": self.ctx.nickname(pid), "text": text,
                                      "kind": kind, "private": private})

    def _system(self, text: str) -> None:
        self.ctx.post_chat(Audience.everyone(), {"from": None, "nickname": "", "text": text,
                                                 "kind": "system", "private": False})

    def _error(self, pid: str, code: str, message: str) -> None:
        self.ctx.send(Audience.of(pid), {"type": "error", "code": code, "message": message})

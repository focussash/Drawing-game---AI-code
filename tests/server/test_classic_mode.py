from server.audience import Audience
from tests.server.helpers import last, last_chat, last_with_audience, make_game


def choose(mode, ctx, clock):
    mode.on_action(ctx.players[0] if mode.drawer is None else mode.drawer, "choose", {"index": 0}, clock.now())


def chat(mode, clock, pid, text):
    mode.on_chat(pid, text, clock.now())


def tick(mode, clock, seconds=0):
    clock.advance(seconds)
    mode.on_tick(clock.now())


def test_start_enters_choosing():
    mode, ctx, clock = make_game(words=("长颈鹿", "熊猫", "苹果"), word_choices=3)
    ph = last(ctx, "phase")
    assert (ph["phase"], ph["drawer"], ph["round"], ph["rounds"]) == ("choosing", "p1", 1, 3)
    assert ph["remaining_ms"] == 15000 and ph["template"] is None
    audience, choices = last_with_audience(ctx, "choices")
    assert audience == Audience.of("p1") and len(choices["words"]) == 3
    assert ctx.canvas_clears == 1


def test_choose_starts_drawing():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    ph = last(ctx, "phase")
    assert ph["phase"] == "drawing" and ph["remaining_ms"] == 80000 and ph["template"] == ["_", "_", "_"]
    assert last(ctx, "word", "p1")["word"] == "长颈鹿"
    assert last(ctx, "word", "p2") is None


def test_choose_by_non_drawer_rejected():
    mode, ctx, clock = make_game()
    mode.on_action("p2", "choose", {"index": 0}, clock.now())
    assert last(ctx, "error", "p2")["code"] == "not_allowed"
    assert last(ctx, "phase")["phase"] == "choosing"


def test_choose_bad_index_and_unknown_action():
    mode, ctx, clock = make_game()
    mode.on_action("p1", "choose", {"index": 7}, clock.now())
    assert last(ctx, "error", "p1")["code"] == "bad_message"
    mode.on_action("p1", "dance", {}, clock.now())
    assert last(ctx, "error", "p1")["code"] == "bad_message"
    assert last(ctx, "phase")["phase"] == "choosing"


def test_choose_timeout_auto_picks():
    mode, ctx, clock = make_game()
    tick(mode, clock, 14.9)
    assert last(ctx, "phase")["phase"] == "choosing"
    tick(mode, clock, 0.1)
    assert last(ctx, "phase")["phase"] == "drawing"


def test_correct_guess_masked_and_scored():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    clock.advance(10)
    chat(mode, clock, "p2", "是长颈鹿吗")
    audience, entry = last_chat(ctx)
    assert audience == Audience.everyone()
    assert entry == {"from": "p2", "nickname": "Np2", "text": "***", "kind": "correct", "private": False}
    assert last(ctx, "word", "p2")["word"] == "长颈鹿"
    sc = last(ctx, "scores")
    assert sc["scores"]["p2"] == 88 and sc["scores"]["p1"] == 25 and sc["correct"] == ["p2"]


def test_wrong_guess_public():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    chat(mode, clock, "p2", "熊")
    audience, entry = last_chat(ctx)
    assert audience == Audience.everyone()
    assert (entry["kind"], entry["text"], entry["private"]) == ("chat", "熊", False)


def test_knower_message_with_answer_stays_private():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    chat(mode, clock, "p2", "长颈鹿")
    before = dict(last(ctx, "scores")["scores"])
    chat(mode, clock, "p2", "长颈鹿好难")
    audience, entry = last_chat(ctx)
    assert audience == Audience.of("p1", "p2") and entry["private"] and entry["text"] == "长颈鹿好难"
    chat(mode, clock, "p1", "长颈鹿")
    audience, entry = last_chat(ctx)
    assert audience == Audience.of("p1", "p2") and entry["private"]
    assert last(ctx, "scores")["scores"] == before


def test_chat_public_outside_drawing():
    mode, ctx, clock = make_game()
    chat(mode, clock, "p2", "长颈鹿")  # choosing
    audience, entry = last_chat(ctx)
    assert audience == Audience.everyone() and entry["kind"] == "chat"
    choose(mode, ctx, clock)
    tick(mode, clock, 80)  # turn_end
    chat(mode, clock, "p1", "长颈鹿")
    audience, entry = last_chat(ctx)
    assert audience == Audience.everyone() and entry["kind"] == "chat"
    assert last(ctx, "scores")["scores"] == {"p1": 0, "p2": 0, "p3": 0}


def test_first_correct_shortens_timer():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    clock.advance(10)
    chat(mode, clock, "p2", "长颈鹿")
    assert last(ctx, "timer")["remaining_ms"] == 20000
    assert mode.snapshot_for("p3", clock.now())["remaining_ms"] == 20000


def test_shorten_disabled_keeps_time():
    mode, ctx, clock = make_game(shorten_after_first_correct=False)
    choose(mode, ctx, clock)
    clock.advance(10)
    chat(mode, clock, "p2", "长颈鹿")
    assert mode.snapshot_for("p3", clock.now())["remaining_ms"] == 70000


def test_all_correct_ends_turn():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    chat(mode, clock, "p2", "长颈鹿")
    chat(mode, clock, "p3", "长颈鹿")
    assert last(ctx, "phase")["phase"] == "turn_end"
    tr = last(ctx, "turn_result")
    assert tr["reason"] == "all_correct" and tr["word"] == "长颈鹿" and tr["drawer"] == "p1"
    assert set(tr["deltas"]) == {"p1", "p2", "p3"} and tr["deltas"]["p1"] == 50


def test_time_up_then_next_turn():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    tick(mode, clock, 80)
    assert last(ctx, "turn_result")["reason"] == "time"
    ph = last(ctx, "phase")
    assert ph["phase"] == "turn_end" and ph["remaining_ms"] == 6000
    tick(mode, clock, 6)
    ph = last(ctx, "phase")
    assert ph["phase"] == "choosing" and ph["drawer"] == "p2"


def test_reveal_penalizes_later_guesses():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    mode.on_action("p1", "reveal", {"index": 1}, clock.now())
    audience, hint = last_with_audience(ctx, "hint")
    assert audience == Audience.everyone() and hint["template"] == ["_", "颈", "_"]
    chat(mode, clock, "p2", "长颈鹿")
    scores = last(ctx, "scores")["scores"]
    assert scores["p2"] == 75 and scores["p1"] == 19


def test_reveal_shown_even_without_length_hint():
    mode, ctx, clock = make_game(show_length_hint=False)
    choose(mode, ctx, clock)
    assert last(ctx, "phase")["template"] is None
    mode.on_action("p1", "reveal", {"index": 0}, clock.now())
    assert last(ctx, "hint")["template"] == ["长", "_", "_"]


def test_reveal_rejected_for_guesser_and_last_char():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    mode.on_action("p2", "reveal", {"index": 0}, clock.now())
    assert last(ctx, "error", "p2")["code"] == "not_allowed"
    mode.on_action("p1", "reveal", {"index": 0}, clock.now())
    mode.on_action("p1", "reveal", {"index": 1}, clock.now())
    mode.on_action("p1", "reveal", {"index": 2}, clock.now())
    assert last(ctx, "error", "p1")["code"] == "not_allowed"
    assert last(ctx, "hint")["template"] == ["长", "颈", "_"]


def test_extend_up_to_limit():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    for _ in range(3):
        mode.on_action("p1", "extend", {}, clock.now())
    timer = last(ctx, "timer")
    assert timer["remaining_ms"] == 110000 and timer["extends_left"] == 0
    assert sum(1 for _, e in ctx.chats if e["kind"] == "system") == 3
    mode.on_action("p1", "extend", {}, clock.now())
    assert last(ctx, "error", "p1")["code"] == "not_allowed"
    assert mode.snapshot_for("p2", clock.now())["remaining_ms"] == 110000


def test_extend_only_by_drawer():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    mode.on_action("p2", "extend", {}, clock.now())
    assert last(ctx, "error", "p2")["code"] == "not_allowed"


def test_host_skip():
    mode, ctx, clock = make_game()
    mode.on_action("p2", "skip", {}, clock.now())
    assert last(ctx, "error", "p2")["code"] == "not_allowed"
    mode.on_action("p1", "skip", {}, clock.now())  # during choosing
    tr = last(ctx, "turn_result")
    assert tr["reason"] == "skipped" and tr["word"] is None
    tick(mode, clock, 6)
    mode.on_action("p2", "choose", {"index": 0}, clock.now())
    mode.on_action("p1", "skip", {}, clock.now())  # host, not drawer, during drawing
    assert last(ctx, "turn_result")["reason"] == "skipped"


def test_drawer_offline_skips_after_grace():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    ctx.go_offline("p1")
    mode.on_player_offline("p1", clock.now())
    assert mode.next_deadline() == clock.now() + 15
    tick(mode, clock, 14)
    assert last(ctx, "phase")["phase"] == "drawing"
    tick(mode, clock, 1)
    assert last(ctx, "turn_result")["reason"] == "drawer_left"


def test_drawer_back_within_grace_continues():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    ctx.go_offline("p1")
    mode.on_player_offline("p1", clock.now())
    clock.advance(10)
    ctx.go_online("p1")
    mode.on_player_online("p1", clock.now())
    tick(mode, clock, 10)
    assert last(ctx, "phase")["phase"] == "drawing"


def test_offline_player_skipped_in_rotation():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    ctx.go_offline("p2")
    mode.on_player_offline("p2", clock.now())
    tick(mode, clock, 80)
    tick(mode, clock, 6)
    assert last(ctx, "phase")["drawer"] == "p3"


def test_briefly_offline_player_still_counts_for_min_players():
    mode, ctx, clock = make_game(players=("p1", "p2"))
    choose(mode, ctx, clock)
    clock.advance(79)
    ctx.go_offline("p2")
    mode.on_player_offline("p2", clock.now())
    tick(mode, clock, 1)
    tick(mode, clock, 6)
    ph = last(ctx, "phase")
    assert ctx.finished is None
    assert (ph["phase"], ph["drawer"], ph["round"]) == ("choosing", "p1", 2)
    choose(mode, ctx, clock)
    tick(mode, clock, 80)
    tick(mode, clock, 6)  # p2 offline for 93s now: away
    assert ctx.finished is not None


def test_game_finishes_after_rounds():
    mode, ctx, clock = make_game(players=("p1", "p2"), rounds=1)
    tick(mode, clock, 15)  # auto choose
    chat(mode, clock, "p2", "长颈鹿")  # only guesser → all_correct
    assert last(ctx, "turn_result")["reason"] == "all_correct"
    tick(mode, clock, 6)
    assert last(ctx, "phase")["drawer"] == "p2"
    tick(mode, clock, 15)
    tick(mode, clock, 80)
    assert ctx.finished is None
    tick(mode, clock, 6)
    assert ctx.finished == [{"id": "p2", "score": 100}, {"id": "p1", "score": 25}]
    assert mode.next_deadline() is None


def test_late_joiner_guesses_now_draws_later():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    ctx.players.append("p4")
    ctx.online["p4"] = True
    mode.on_player_joined("p4", clock.now())
    chat(mode, clock, "p4", "长颈鹿")
    assert last(ctx, "scores")["scores"]["p4"] > 0
    drawers = []
    for _ in range(3):
        mode.on_action("p1", "skip", {}, clock.now())
        tick(mode, clock, 6)
        drawers.append(last(ctx, "phase")["drawer"])
    assert drawers == ["p2", "p3", "p4"]


def test_removed_drawer_ends_turn():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    ctx.players.remove("p1")
    mode.on_player_removed("p1", clock.now())
    assert last(ctx, "turn_result")["reason"] == "drawer_left"


def test_removed_last_guesser_completes_turn():
    mode, ctx, clock = make_game()
    choose(mode, ctx, clock)
    chat(mode, clock, "p2", "长颈鹿")
    ctx.players.remove("p3")
    mode.on_player_removed("p3", clock.now())
    assert last(ctx, "turn_result")["reason"] == "all_correct"
    assert "p3" not in last(ctx, "scores")["scores"]


def test_snapshot_hides_word():
    mode, ctx, clock = make_game(words=("长颈鹿", "熊猫"), word_choices=2)
    assert "choices" in mode.snapshot_for("p1", clock.now())
    assert "choices" not in mode.snapshot_for("p2", clock.now())
    choose(mode, ctx, clock)
    guesser = mode.snapshot_for("p2", clock.now())
    assert guesser["template"] is not None and "word" not in guesser and guesser["phase"] == "drawing"
    drawer = mode.snapshot_for("p1", clock.now())
    assert drawer["word"] == mode.word and drawer["extends_left"] == 3
    assert set(guesser) >= {"phase", "round", "rounds", "drawer", "remaining_ms", "template", "scores", "correct"}


def test_can_draw_only_drawer_while_drawing():
    mode, ctx, clock = make_game()
    assert not mode.can_draw("p1")
    choose(mode, ctx, clock)
    assert mode.can_draw("p1") and not mode.can_draw("p2")
    tick(mode, clock, 80)
    assert not mode.can_draw("p1")


def test_words_not_repeated():
    mode, ctx, clock = make_game(words=("A", "B"))
    choose(mode, ctx, clock)
    first = mode.word
    mode.on_action("p1", "skip", {}, clock.now())
    tick(mode, clock, 6)
    choose(mode, ctx, clock)
    assert {first, mode.word} == {"A", "B"}

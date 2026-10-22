import pytest

from server.modes.classic.hints import HintError, WordHint
from server.modes.classic.judge import is_correct
from server.modes.classic.rotation import Rotation
from server.modes.classic.scoring import drawer_points, guesser_points
from server.modes.classic.settings import ScoringConfig
from server.modes.classic.turn_timer import TurnTimer

CFG = ScoringConfig(guesser_max=100, guesser_min=20, drawer_per_guess=25, reveal_factor=0.75)


def test_guesser_points():
    cases = [(80, 0), (40, 0), (8, 0), (100, 0), (80, 1), (80, 2)]
    assert [guesser_points(r, 80, k, CFG) for r, k in cases] == [100, 50, 20, 100, 75, 56]


def test_drawer_points():
    assert [drawer_points(k, CFG) for k in (0, 1, 2)] == [25, 19, 14]


def test_timer_shorten_and_extend():
    t = TurnTimer()
    t.start(0, 80)
    assert t.remaining(30) == 50
    t.shorten_to(30, 20)
    assert t.remaining(30) == 20
    t.extend(10)
    assert t.remaining(30) == 30 and t.extends_used == 1
    assert not t.expired(59.9) and t.expired(60)


def test_shorten_never_lengthens():
    t = TurnTimer()
    t.start(0, 80)
    t.shorten_to(70, 20)
    assert t.remaining(70) == 10


def test_timer_start_resets_extends_and_remaining_floors_at_zero():
    t = TurnTimer()
    t.start(0, 80)
    t.extend(10)
    t.start(100, 80)
    assert t.extends_used == 0 and t.remaining(500) == 0


def test_hint_template_and_reveal():
    h = WordHint("长颈鹿")
    assert h.template(True) == ["_", "_", "_"] and h.template(False) is None
    h.reveal(1)
    assert h.template(False) == ["_", "颈", "_"] and h.reveals == 1
    for bad in (1, 5, -1):
        with pytest.raises(HintError):
            h.reveal(bad)
    h.reveal(0)
    with pytest.raises(HintError):
        h.reveal(2)


def test_hint_spaces_and_single_char():
    h = WordHint("hello kitty")
    assert h.template(True)[5] == " "
    with pytest.raises(HintError):
        h.reveal(5)
    assert not WordHint("猫").can_reveal_more()
    assert WordHint("长颈鹿").can_reveal_more()


@pytest.mark.parametrize("guess", ["长颈鹿", "是不是 长颈鹿！", "长颈鹿吧"])
def test_is_correct_contains(guess):
    assert is_correct(guess, "长颈鹿")


def test_is_correct_width_case():
    assert is_correct("ＨＥＬＬＯ Kitty", "hello kitty")


@pytest.mark.parametrize("guess, answer", [("长颈", "长颈鹿"), ("", "长颈鹿"), ("!!!", "!!")])
def test_is_correct_rejects(guess, answer):
    assert not is_correct(guess, answer)


def test_rotation_rounds():
    r = Rotation(2)
    ids = ["a", "b", "c"]
    r.start(ids)
    assert r.round == 1
    assert [r.next_drawer(ids, lambda p: True) for _ in range(6)] == ["a", "b", "c", "a", "b", "c"]
    assert r.next_drawer(ids, lambda p: True) is None and r.round == 2


def test_rotation_skips_ineligible():
    r = Rotation(1)
    ids = ["a", "b", "c"]
    r.start(ids)
    el = lambda p: p != "b"  # noqa: E731
    assert [r.next_drawer(ids, el), r.next_drawer(ids, el)] == ["a", "c"]


def test_rotation_late_join_and_remove():
    r = Rotation(1)
    ids = ["a", "b"]
    r.start(ids)
    assert r.next_drawer(ids, lambda p: True) == "a"
    r.add_late("d")
    r.add_late("a")
    r.remove("b")
    assert r.next_drawer(ids + ["d"], lambda p: True) == "d"
    assert r.next_drawer(ids, lambda p: True) is None


def test_rotation_no_one_eligible_ends():
    r = Rotation(3)
    r.start(["a", "b"])
    assert r.next_drawer(["a", "b"], lambda p: False) is None

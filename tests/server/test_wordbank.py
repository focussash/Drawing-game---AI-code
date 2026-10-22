from random import Random

import pytest

from server.wordbank import UnknownBank, WordPool, list_banks, load_bank, load_banks


def test_list_banks_sorted_txt_stems(tmp_path):
    for name in ["b.txt", "a.txt", "notes.md"]:
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert list_banks(tmp_path) == ["a", "b"]


def test_list_banks_missing_dir_is_empty(tmp_path):
    assert list_banks(tmp_path / "nope") == []


def test_load_bank_handles_bom_crlf_comments(tmp_path):
    (tmp_path / "a.txt").write_bytes("\ufeff# 注释\r\n苹果\r\n\r\n香蕉\n苹果\n！！\n".encode("utf-8"))
    assert load_bank(tmp_path, "a") == ["苹果", "香蕉"]


def test_load_bank_falls_back_to_gbk(tmp_path):
    (tmp_path / "g.txt").write_bytes("长颈鹿\n熊猫\n".encode("gbk"))
    assert load_bank(tmp_path, "g") == ["长颈鹿", "熊猫"]


def test_load_bank_rejects_unknown_and_traversal(tmp_path):
    (tmp_path / "a.txt").write_text("x", encoding="utf-8")
    for name in ["missing", "../secret", "a/b", "a.txt"]:
        with pytest.raises(UnknownBank):
            load_bank(tmp_path, name)


def test_load_banks_union_dedup(tmp_path):
    (tmp_path / "a.txt").write_text("苹果\n香蕉\n", encoding="utf-8")
    (tmp_path / "b.txt").write_text("香蕉\n熊猫\n", encoding="utf-8")
    assert load_banks(tmp_path, ["a", "b"]) == ["苹果", "香蕉", "熊猫"]


def test_pool_draws_distinct():
    assert len(set(WordPool(list("abc"), Random(0)).draw(2))) == 2


def test_pool_prefers_unused_then_refills():
    pool = WordPool(["a", "b", "c"], Random(0))
    pool.mark_used("a")
    pool.mark_used("b")
    assert pool.draw(1) == ["c"]
    three = pool.draw(3)
    assert "c" in three and len(set(three)) == 3


def test_pool_smaller_than_n():
    assert WordPool(["a"], Random(0)).draw(3) == ["a"]


def test_pool_size():
    assert WordPool(["a", "b"], Random(0)).size == 2


def test_bundled_default_bank_is_usable():
    from pathlib import Path

    from server.textnorm import normalize

    words_dir = Path(__file__).resolve().parents[2] / "words"
    words = load_bank(words_dir, "默认")
    assert len(words) >= 200
    assert all(normalize(w) for w in words)

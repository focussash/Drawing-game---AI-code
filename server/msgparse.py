"""Field validation for client messages. Every failure raises BadMessage."""

from __future__ import annotations

from typing import Any


class BadMessage(Exception):
    pass


def req_str(d: dict, key: str, max_len: int, allow_blank: bool = False) -> str:
    value = d.get(key)
    if not isinstance(value, str) or len(value) > max_len:
        raise BadMessage(key)
    if not allow_blank and not value.strip():
        raise BadMessage(key)
    return value


def req_int(d: dict, key: str, lo: int, hi: int) -> int:
    value = d.get(key)
    if not _is_int(value) or not lo <= value <= hi:
        raise BadMessage(key)
    return value


def req_int_list(d: dict, key: str, max_len: int, lo: int, hi: int) -> list[int]:
    value = d.get(key)
    if not isinstance(value, list) or len(value) > max_len:
        raise BadMessage(key)
    if not all(_is_int(v) and lo <= v <= hi for v in value):
        raise BadMessage(key)
    return value


def req_dict(d: dict, key: str) -> dict:
    value = d.get(key)
    if not isinstance(value, dict):
        raise BadMessage(key)
    return value


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)

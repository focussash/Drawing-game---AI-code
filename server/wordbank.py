"""Word banks: each words/<name>.txt is one bank, one word per line."""

from __future__ import annotations

import random
from pathlib import Path

from server.textnorm import normalize

_ENCODINGS = ("utf-8-sig", "gb18030")


class UnknownBank(Exception):
    """The requested bank name is not a .txt file in the words directory."""


def list_banks(words_dir: Path) -> list[str]:
    words_dir = Path(words_dir)
    if not words_dir.is_dir():
        return []
    return sorted(p.stem for p in words_dir.glob("*.txt") if p.is_file())


def load_bank(words_dir: Path, name: str) -> list[str]:
    # Only names that list_banks() reports are readable, which rules out
    # path tricks like "../x".
    if name not in list_banks(words_dir):
        raise UnknownBank(name)
    text = _decode((Path(words_dir) / f"{name}.txt").read_bytes())
    words: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        word = line.strip()
        if not word or word.startswith("#") or not normalize(word) or word in seen:
            continue
        seen.add(word)
        words.append(word)
    return words


def load_banks(words_dir: Path, names: list[str]) -> list[str]:
    words: list[str] = []
    seen: set[str] = set()
    for name in names:
        for word in load_bank(words_dir, name):
            if word not in seen:
                seen.add(word)
                words.append(word)
    return words


def _decode(data: bytes) -> str:
    for encoding in _ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


class WordPool:
    """Draws word choices for one game, avoiding repeats until words run out."""

    def __init__(self, words: list[str], rng: random.Random):
        self._words = list(words)
        self._rng = rng
        self._used: set[str] = set()

    @property
    def size(self) -> int:
        return len(self._words)

    def draw(self, n: int) -> list[str]:
        unused = [w for w in self._words if w not in self._used]
        picked = self._rng.sample(unused, min(n, len(unused)))
        if len(picked) < n:
            used = [w for w in self._words if w in self._used]
            picked += self._rng.sample(used, min(n - len(picked), len(used)))
        return picked

    def mark_used(self, word: str) -> None:
        self._used.add(word)

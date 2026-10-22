"""Text helpers shared by word banks and guess judging."""

from __future__ import annotations

import unicodedata

# Unicode general categories dropped by normalize(): punctuation, symbols,
# separators (spaces) and control/format characters.
_DROPPED_CATEGORIES = ("P", "S", "Z", "C")


def normalize(text: str) -> str:
    """Fold width and case, then drop spaces, punctuation and symbols."""
    folded = unicodedata.normalize("NFKC", text).casefold()
    return "".join(ch for ch in folded if not unicodedata.category(ch).startswith(_DROPPED_CATEGORIES))


def word_length(word: str) -> int:
    """Number of characters in a word, not counting whitespace."""
    return sum(1 for ch in word if not ch.isspace())


def mask(word: str) -> str:
    """One star per character, so a correct guess hides the answer."""
    return "*" * word_length(word)

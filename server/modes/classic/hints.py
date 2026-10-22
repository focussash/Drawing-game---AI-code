"""What guessers see of the word: blanks, gaps for spaces, and characters the drawer revealed."""

from __future__ import annotations

from server.textnorm import word_length


class HintError(Exception):
    pass


class WordHint:
    def __init__(self, word: str):
        self.word = word
        self._revealed: set[int] = set()

    @property
    def reveals(self) -> int:
        return len(self._revealed)

    def can_reveal_more(self) -> bool:
        return self.reveals < word_length(self.word) - 1

    def reveal(self, index: int) -> None:
        if not 0 <= index < len(self.word):
            raise HintError("没有这个位置")
        if self.word[index].isspace():
            raise HintError("空格不能揭示")
        if index in self._revealed:
            raise HintError("这个字已经揭示过了")
        if not self.can_reveal_more():
            raise HintError("不能把字全部揭示")
        self._revealed.add(index)

    def template(self, show_length: bool) -> list[str] | None:
        if not show_length and not self._revealed:
            return None
        return [" " if ch.isspace() else (ch if i in self._revealed else "_")
                for i, ch in enumerate(self.word)]

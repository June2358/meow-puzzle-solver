"""Puzzle-independent outcome and typed trace passed to the application UI."""

from dataclasses import dataclass
from enum import StrEnum


class Outcome(StrEnum):
    UNIQUE = "unique"
    MULTIPLE = "multiple"
    UNSOLVABLE = "unsolvable"


@dataclass(frozen=True, slots=True)
class PlaybackData[Frame]:
    outcome: Outcome
    frames: tuple[Frame, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, Outcome):
            raise TypeError("해 분류는 Outcome이어야 합니다.")
        if not isinstance(self.frames, tuple):
            raise TypeError("풀이 단계는 tuple이어야 합니다.")
        if not self.frames:
            raise ValueError("풀이 단계는 비어 있을 수 없습니다.")

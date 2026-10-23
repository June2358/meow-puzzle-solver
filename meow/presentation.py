"""Adapt MEOW's solver result without changing its domain trace."""

from puzzle_common.presentation import Outcome, PlaybackData

from .exact_solver import ExactStatus
from .solver import SolveResult
from .timeline import PlaybackFrame, build_timeline


def to_playback(result: SolveResult) -> PlaybackData[PlaybackFrame]:
    if not isinstance(result, SolveResult):
        raise TypeError("MEOW 풀이 결과가 필요합니다.")
    outcome = {
        ExactStatus.UNIQUE: Outcome.UNIQUE,
        ExactStatus.MULTIPLE: Outcome.MULTIPLE,
        ExactStatus.UNSOLVABLE: Outcome.UNSOLVABLE,
    }[result.exact_result.status]
    return PlaybackData(outcome, build_timeline(result))

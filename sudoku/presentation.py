"""Adapt Sudoku's result while retaining its exact immutable step tuple."""

from puzzle_common.presentation import Outcome, PlaybackData

from .solve_types import SolveResult, SolveStatus, SolveStep


def to_playback(result: SolveResult) -> PlaybackData[SolveStep]:
    if not isinstance(result, SolveResult):
        raise TypeError("Sudoku 풀이 결과가 필요합니다.")
    outcome = {
        SolveStatus.SOLVED_UNIQUE: Outcome.UNIQUE,
        SolveStatus.SOLVED_MULTIPLE: Outcome.MULTIPLE,
        SolveStatus.UNSOLVABLE: Outcome.UNSOLVABLE,
    }[result.status]
    return PlaybackData(outcome, result.steps)

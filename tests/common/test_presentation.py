from dataclasses import FrozenInstanceError

import pytest
from sample_puzzles import UNIQUE_GRID, UNIQUE_SOLUTION

from meow.model import Puzzle as RegionPuzzle
from meow.presentation import to_playback as region_playback
from meow.puzzle_catalog import load_preset
from meow.solver import solve
from meow.timeline import build_timeline
from puzzle_common.presentation import Outcome, PlaybackData
from sudoku.board import Puzzle as DigitPuzzle
from sudoku.presentation import to_playback as digit_playback
from sudoku.solver import SudokuSolver


@pytest.mark.parametrize("outcome", tuple(Outcome))
def test_region_results_use_common_outcome_without_changing_trace(outcome):
    if outcome is Outcome.UNIQUE:
        puzzle = load_preset("쉬움")
    else:
        size = 2 if outcome is Outcome.UNSOLVABLE else 4
        puzzle = RegionPuzzle.from_region_grid(
            tuple(tuple(chr(65 + col) for col in range(size)) for _ in range(size))
        )
    result = solve(puzzle)

    data = region_playback(result)

    assert data.outcome is outcome
    assert data.frames == build_timeline(result)
    assert data.frames[0].snapshot.puzzle.region_grid == puzzle.region_grid


@pytest.mark.parametrize("outcome", tuple(Outcome))
def test_digit_results_keep_exact_solver_steps(outcome):
    grid = [list(row) for row in UNIQUE_SOLUTION]
    if outcome is Outcome.UNIQUE:
        grid = UNIQUE_GRID
    elif outcome is Outcome.MULTIPLE:
        for row, col in ((0, 3), (0, 4), (3, 3), (3, 4)):
            grid[row][col] = 0
    else:
        grid[0][0], grid[0][7], grid[2][0] = 1, 0, 0
    puzzle = DigitPuzzle(grid)
    result = SudokuSolver(puzzle).solve()

    data = digit_playback(result)

    assert data.outcome is outcome
    assert data.frames is result.steps
    assert data.frames[0].grid == puzzle.grid


def test_playback_data_is_immutable_and_rejects_empty_trace():
    with pytest.raises(ValueError, match="단계"):
        PlaybackData(Outcome.UNIQUE, ())
    data = PlaybackData(Outcome.UNIQUE, (object(),))
    with pytest.raises(FrozenInstanceError):
        data.outcome = Outcome.MULTIPLE


@pytest.mark.parametrize(
    ("outcome", "frames"),
    (("unique", (object(),)), (Outcome.UNIQUE, [object()])),
)
def test_playback_data_rejects_untyped_outcomes_and_mutable_frames(outcome, frames):
    with pytest.raises(TypeError):
        PlaybackData(outcome, frames)


@pytest.mark.parametrize("adapter", (region_playback, digit_playback))
def test_result_adapter_rejects_a_foreign_result(adapter):
    with pytest.raises(TypeError):
        adapter(object())

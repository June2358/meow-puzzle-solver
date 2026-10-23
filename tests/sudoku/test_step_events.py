from sample_puzzles import UNIQUE_SOLUTION, grid_from_string

from puzzle_common.engine import LogicStatus, Outcome
from puzzle_common.presentation import FrameKind, build_frames
from sudoku.board import Puzzle
from sudoku.solver import SudokuSolver

REFUTATION_THEN_SOLUTION = (
    "800400057250000640097300800000070406000905000904060000008001720019000085530007004"
)


def test_refutation_removes_the_proven_candidate() -> None:
    result = SudokuSolver(Puzzle(grid_from_string(REFUTATION_THEN_SOLUTION))).solve()
    frames = build_frames(result)
    refutation = next(frame for frame in frames if frame.kind is FrameKind.REFUTATION)
    contradictions = tuple(
        frame
        for frame in frames
        if frame.kind in (FrameKind.LOGIC_END, FrameKind.PROBE_END)
        and frame.status is LogicStatus.CONTRADICTION
    )

    assert result.outcome is Outcome.UNIQUE
    assert contradictions
    assert all(step.contradiction is not None for step in contradictions)
    assert refutation.active_assumption is None
    assert refutation.assumption is not None
    row, col = refutation.assumption.cell
    assert refutation.assumption.value not in refutation.snapshot[1][row][col]
    assert FrameKind.SEARCH not in {frame.kind for frame in frames}


def test_assumption_solution_is_still_checked_for_a_second_solution() -> None:
    grid = [list(row) for row in UNIQUE_SOLUTION]
    for row, col in ((0, 3), (0, 4), (3, 3), (3, 4)):
        grid[row][col] = 0

    result = SudokuSolver(Puzzle(grid)).solve()
    frames = build_frames(result)
    kinds = [frame.kind for frame in frames]
    branch_solution = next(
        frame.snapshot
        for frame in frames
        if frame.kind is FrameKind.PROBE_END and frame.status is LogicStatus.SOLVED
    )

    assert FrameKind.PROBE_END in kinds
    assert FrameKind.SEARCH not in kinds
    assert result.outcome is Outcome.MULTIPLE
    assert result.solution == branch_solution == frames[-1].snapshot

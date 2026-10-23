from sample_puzzles import UNIQUE_SOLUTION, grid_from_string

from sudoku.board import Puzzle
from sudoku.solve_types import SolveStatus, StepKind
from sudoku.solver import SudokuSolver

REFUTATION_THEN_SOLUTION = (
    "800400057250000640097300800000070406000905000904060000008001720019000085530007004"
)


def test_refutation_removes_the_proven_candidate() -> None:
    result = SudokuSolver(Puzzle(grid_from_string(REFUTATION_THEN_SOLUTION))).solve()
    refutation = next(step for step in result.steps if step.kind is StepKind.REFUTATION)
    contradictions = tuple(
        step for step in result.steps if step.kind is StepKind.CONTRADICTION
    )

    assert result.status is SolveStatus.SOLVED_UNIQUE
    assert contradictions
    assert all(step.contradiction is not None for step in contradictions)
    assert refutation.assumption is not None
    row, col = refutation.assumption.cell
    assert refutation.assumption.value not in refutation.candidates[row][col]
    assert StepKind.SEARCH_FALLBACK not in {step.kind for step in result.steps}


def test_assumption_solution_is_still_checked_for_a_second_solution() -> None:
    grid = [list(row) for row in UNIQUE_SOLUTION]
    for row, col in ((0, 3), (0, 4), (3, 3), (3, 4)):
        grid[row][col] = 0

    result = SudokuSolver(Puzzle(grid)).solve()
    kinds = [step.kind for step in result.steps]
    branch_solution = next(
        step.grid for step in result.steps if step.kind is StepKind.ASSUMPTION_SOLVED
    )

    assert StepKind.ASSUMPTION_SOLVED in kinds
    assert StepKind.SEARCH_FALLBACK not in kinds
    assert result.status is SolveStatus.SOLVED_MULTIPLE
    assert result.solution == branch_solution == result.steps[-1].grid

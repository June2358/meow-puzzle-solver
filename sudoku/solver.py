"""Sudoku entry point for the shared solving result and execution engine."""

from puzzle_common.engine import Engine, Outcome, SolveResult

from .board import Puzzle
from .engine_adapter import SudokuDomain
from .solver_state import SolverState


def solve(puzzle: Puzzle) -> SolveResult:
    """Explain Sudoku reasoning and distinguish zero, one, or multiple solutions."""
    if not isinstance(puzzle, Puzzle):
        raise TypeError("Sudoku 솔버는 Puzzle을 받아야 합니다.")
    run = Engine(SudokuDomain()).solve(SolverState(puzzle), solution_limit=2)
    outcome = (
        Outcome.MULTIPLE
        if len(run.solutions) >= 2
        else Outcome.UNIQUE
        if run.solutions
        else Outcome.UNSOLVABLE
    )
    return SolveResult(outcome, run)

"""Sudoku entry point for the shared solving result and execution engine."""

from puzzle_common.engine import Engine, Outcome, SolveResult

from .board import Puzzle
from .engine_adapter import SudokuDomain
from .solver_state import SolverState


class SudokuSolver:
    """Explain Sudoku reasoning and distinguish zero, one, or multiple solutions."""

    __slots__ = ("_puzzle",)

    def __init__(self, puzzle: Puzzle):
        if not isinstance(puzzle, Puzzle):
            raise TypeError("SudokuSolver는 Puzzle을 받아야 합니다.")
        self._puzzle = puzzle

    def solve(self) -> SolveResult:
        run = Engine(SudokuDomain()).solve(SolverState(self._puzzle), solution_limit=2)
        outcome = (
            Outcome.MULTIPLE
            if len(run.solutions) >= 2
            else Outcome.UNIQUE
            if run.solutions
            else Outcome.UNSOLVABLE
        )
        return SolveResult(outcome, run)

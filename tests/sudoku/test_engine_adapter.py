"""The public Sudoku solver uses the shared solving lifecycle."""

import sys

from sample_puzzles import UNIQUE_GRID, UNIQUE_SOLUTION

from sudoku.board import Puzzle
from sudoku.solve_types import SolveStatus
from sudoku.solver import SudokuSolver


def test_public_solver_runs_the_shared_engine() -> None:
    calls = []

    def record_engine_call(frame, event, arg):
        if (
            event == "call"
            and frame.f_globals.get("__name__") == "puzzle_common.engine"
            and frame.f_code.co_name == "solve"
        ):
            calls.append(frame.f_locals["self"])

    previous_profile = sys.getprofile()
    sys.setprofile(record_engine_call)
    try:
        result = SudokuSolver(Puzzle(UNIQUE_GRID)).solve()
    finally:
        sys.setprofile(previous_profile)

    assert result.status is SolveStatus.SOLVED_UNIQUE
    assert result.solution == UNIQUE_SOLUTION
    assert len(calls) == 1

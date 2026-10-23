"""The public Sudoku solver uses the shared solving lifecycle."""

import sys

from sample_puzzles import UNIQUE_GRID, UNIQUE_SOLUTION

from puzzle_common.engine import Outcome, SolveResult
from sudoku.board import Puzzle
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

    assert isinstance(result, SolveResult)
    assert result.outcome is Outcome.UNIQUE
    assert result.solution[0] == UNIQUE_SOLUTION
    assert result.run.solutions[0] == result.solution
    assert len(calls) == 1

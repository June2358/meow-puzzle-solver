"""Measure full solves with correctness checks: python -m scripts.benchmark_solver."""

from statistics import median
from time import perf_counter

from sudoku.board import Puzzle
from sudoku.solve_types import SolveStatus
from sudoku.solver import SudokuSolver
from sudoku.topology import DIGITS, UNITS

# Peter Norvig's examples: https://www.norvig.com/sudoku.html
_CASES = (
    (
        "Norvig hard",
        "4.....8.5.3..........7......2.....6.....8.4......1.......6.3.7.5..2.....1.4......",
        SolveStatus.SOLVED_UNIQUE,
    ),
    (
        "Inkala 2010",
        "..53.....8......2..7..1.5..4....53...1..7...6..32...8..6.5....9..4....3......97..",
        SolveStatus.SOLVED_UNIQUE,
    ),
    ("Empty board", "0" * 81, SolveStatus.SOLVED_MULTIPLE),
)


def main() -> None:
    for name, text, expected_status in _CASES:
        digits = text.replace(".", "0")
        puzzle = Puzzle(
            tuple(
                tuple(int(value) for value in digits[start : start + 9])
                for start in range(0, 81, 9)
            )
        )
        solver = SudokuSolver(puzzle)
        reference = solver.solve()
        assert reference.status is expected_status
        solution = reference.solution
        assert solution is not None
        assert all(
            {solution[row][col] for row, col in unit} == DIGITS for unit in UNITS
        )
        assert all(
            solution[row][col] == puzzle.grid[row][col] for row, col in puzzle.givens
        )

        durations = []
        for _ in range(7):
            started = perf_counter()
            result = solver.solve()
            durations.append(perf_counter() - started)
            assert result == reference
        print(f"{name}: {median(durations) * 1000:.3f} ms (median of 7 full solves)")


if __name__ == "__main__":
    main()

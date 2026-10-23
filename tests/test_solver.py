from sample_puzzles import UNIQUE_GRID, UNIQUE_SOLUTION

from sudoku.board import Puzzle
from sudoku.solve_types import SolveStatus
from sudoku.solver import SudokuSolver
from sudoku.topology import UNITS

# 초기 단서 충돌은 없지만 R1C1 변경으로 R3C1의 후보가 사라진다.
UNSOLVABLE_GRID = [
    [1, 3, 4, 6, 7, 8, 9, 0, 2],
    [6, 7, 2, 1, 9, 5, 3, 4, 8],
    [0, 9, 8, 3, 4, 2, 5, 6, 7],
    [8, 5, 9, 7, 6, 1, 4, 2, 3],
    [4, 2, 6, 8, 5, 3, 7, 9, 1],
    [7, 1, 3, 9, 2, 4, 8, 5, 6],
    [9, 6, 1, 5, 3, 7, 2, 8, 4],
    [2, 8, 7, 4, 1, 9, 6, 3, 5],
    [3, 4, 5, 2, 8, 6, 1, 7, 9],
]

# 복수해를 가진 자명하지 않은 퍼즐.
MULTIPLE_GRID = [
    [0, 9, 0, 0, 3, 2, 0, 0, 1],
    [7, 0, 0, 0, 9, 0, 0, 0, 0],
    [0, 0, 8, 0, 0, 0, 9, 6, 0],
    [5, 0, 0, 0, 4, 0, 0, 0, 0],
    [0, 0, 0, 2, 0, 0, 0, 1, 8],
    [8, 0, 0, 6, 0, 0, 0, 0, 0],
    [0, 6, 0, 0, 0, 0, 0, 5, 4],
    [0, 0, 0, 0, 2, 0, 0, 0, 7],
    [0, 0, 4, 0, 0, 1, 0, 0, 0],
]


def assert_valid_solution(solution, puzzle: Puzzle) -> None:
    assert solution is not None
    expected_digits = set(range(1, 10))
    for unit in UNITS:
        assert {solution[row][col] for row, col in unit} == expected_digits
    for row, col in puzzle.givens:
        assert solution[row][col] == puzzle.grid[row][col]


def test_unique_puzzle_returns_the_unique_solution() -> None:
    puzzle = Puzzle(UNIQUE_GRID)

    result = SudokuSolver(puzzle).solve()

    assert result.status is SolveStatus.SOLVED_UNIQUE
    assert result.solution == UNIQUE_SOLUTION


def test_multiple_puzzle_returns_a_valid_representative() -> None:
    puzzle = Puzzle(MULTIPLE_GRID)

    result = SudokuSolver(puzzle).solve()

    assert result.status is SolveStatus.SOLVED_MULTIPLE
    assert_valid_solution(result.solution, puzzle)


def test_consistent_but_impossible_givens_are_unsolvable() -> None:
    puzzle = Puzzle(UNSOLVABLE_GRID)

    result = SudokuSolver(puzzle).solve()

    assert result.status is SolveStatus.UNSOLVABLE
    assert result.solution is None

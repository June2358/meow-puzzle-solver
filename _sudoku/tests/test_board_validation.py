import pytest

from sudoku.board import (
    InvalidBoardError,
    InvalidPuzzleError,
    Puzzle,
    validate_grid,
)


def empty_grid() -> list[list[int]]:
    return [[0] * 9 for _ in range(9)]


def test_validate_grid_rejects_a_non_9x9_shape() -> None:
    with pytest.raises(InvalidBoardError):
        validate_grid([[0] * 9 for _ in range(8)])


def test_puzzle_rejects_conflicting_givens() -> None:
    grid = empty_grid()
    grid[0][0] = grid[0][8] = 7

    with pytest.raises(InvalidPuzzleError):
        Puzzle(grid)

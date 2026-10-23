import json

import pytest
from sample_puzzles import UNIQUE_GRID

from sudoku.board import InvalidPuzzleError, Puzzle
from sudoku.matrix_parser import MatrixParseError, parse_matrix_json


def test_parse_matrix_json_accepts_a_valid_grid() -> None:
    assert parse_matrix_json(json.dumps(UNIQUE_GRID)) == tuple(
        tuple(row) for row in UNIQUE_GRID
    )


@pytest.mark.parametrize(
    "text",
    [
        "not JSON",
        json.dumps([[0] * 9 for _ in range(8)]),
        json.dumps([[10] + [0] * 8] + [[0] * 9 for _ in range(8)]),
    ],
)
def test_parse_matrix_json_rejects_representative_invalid_inputs(text: str) -> None:
    with pytest.raises(MatrixParseError):
        parse_matrix_json(text)


def test_conflicts_can_be_loaded_for_editing_but_not_as_a_puzzle() -> None:
    matrix = [[0] * 9 for _ in range(9)]
    matrix[0][0] = matrix[0][1] = 4
    text = json.dumps(matrix)

    assert parse_matrix_json(text)[0][:2] == (4, 4)
    with pytest.raises(InvalidPuzzleError):
        Puzzle(parse_matrix_json(text))

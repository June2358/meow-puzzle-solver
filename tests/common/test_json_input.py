import pytest

from meow.parser import PuzzleParseError, parse_puzzle_json
from sudoku.matrix_parser import MatrixParseError, parse_matrix_json


@pytest.mark.parametrize(
    "parse, error_type",
    [(parse_puzzle_json, PuzzleParseError), (parse_matrix_json, MatrixParseError)],
)
@pytest.mark.parametrize(
    "text",
    ["[" * 2000 + "]" * 2000, "1" * 5000],
    ids=["deeply_nested", "oversized_integer"],
)
def test_complex_external_json_raises_the_app_parse_error(parse, error_type, text):
    with pytest.raises(error_type):
        parse(text)

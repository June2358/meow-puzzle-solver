"""Strict parser for the external AI/OCR matrix contract."""

from puzzle_common.json_input import decode_json

from .board import Grid, InvalidBoardError, validate_grid


class MatrixParseError(ValueError):
    """Raised when AI/OCR JSON is not one raw 9x9 integer matrix."""


def parse_matrix_json(text: str) -> Grid:
    """Parse a raw JSON 9x9 integer array without applying Sudoku rules."""

    decoded = decode_json(text, MatrixParseError)

    if type(decoded) is not list:
        raise MatrixParseError("최상위 JSON 값은 9개 행을 가진 배열이어야 합니다.")
    if any(type(row) is not list for row in decoded):
        raise MatrixParseError("JSON의 각 행은 배열이어야 합니다.")

    try:
        return validate_grid(decoded)
    except InvalidBoardError as exc:
        raise MatrixParseError(str(exc)) from exc

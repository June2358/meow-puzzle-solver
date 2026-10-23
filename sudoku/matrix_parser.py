"""외부 AI/OCR 행렬 계약을 엄격히 검사하는 파서."""

import json

from .board import Grid, InvalidBoardError, validate_grid


class MatrixParseError(ValueError):
    """AI/OCR JSON이 단일 9×9 정수 행렬이 아닐 때 발생한다."""


def parse_matrix_json(text: str) -> Grid:
    """스도쿠 규칙 적용 없이 JSON 9×9 정수 배열의 형식을 검사한다."""

    if not isinstance(text, str):
        raise TypeError("매트릭스 JSON은 str이어야 합니다.")

    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as exc:
        raise MatrixParseError(
            f"올바른 JSON 배열이 아닙니다: {exc.msg} (줄 {exc.lineno}, 열 {exc.colno})"
        ) from exc
    except (ValueError, RecursionError) as exc:
        raise MatrixParseError(
            "JSON 숫자가 너무 길거나 배열이 너무 깊게 중첩되어 있습니다."
        ) from exc

    if type(decoded) is not list:
        raise MatrixParseError("최상위 JSON 값은 9개 행을 가진 배열이어야 합니다.")
    if any(type(row) is not list for row in decoded):
        raise MatrixParseError("JSON의 각 행은 배열이어야 합니다.")

    try:
        return validate_grid(decoded)
    except InvalidBoardError as exc:
        raise MatrixParseError(str(exc)) from exc

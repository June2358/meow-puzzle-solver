"""표준 JSON Queens 퍼즐 형식 파서."""

from __future__ import annotations

import json

from .model import InvalidRegionMapError, Puzzle


class PuzzleParseError(InvalidRegionMapError):
    """입력을 퍼즐 문서로 해석할 수 없을 때 발생한다."""


def parse_puzzle_json(text: str) -> Puzzle:
    """표준 JSON 퍼즐 객체를 파싱한다.

    객체에는 영역 라벨 문자열의 2차원 배열인 ``regions`` 필드만 허용한다.
    메타데이터나 해 필드는 받지 않는다."""

    if not isinstance(text, str):
        raise TypeError("JSON 퍼즐 입력은 문자열이어야 합니다.")

    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise PuzzleParseError(
            f"올바른 JSON이 아닙니다: {error.lineno}행 {error.colno}열"
        ) from error
    except (RecursionError, ValueError) as error:
        raise PuzzleParseError(
            "JSON이 너무 복잡하거나 지원하지 않는 값이 있습니다."
        ) from error

    if not isinstance(document, dict):
        raise PuzzleParseError("JSON 최상위 값은 객체여야 합니다.")

    unknown_fields = document.keys() - {"regions"}
    if unknown_fields:
        fields = ", ".join(sorted(repr(field) for field in unknown_fields))
        raise PuzzleParseError(f"지원하지 않는 JSON 필드입니다: {fields}")
    if "regions" not in document:
        raise PuzzleParseError("JSON 객체에는 'regions' 필드가 필요합니다.")

    regions = document["regions"]
    if not isinstance(regions, list):
        raise PuzzleParseError("JSON의 'regions'는 행 배열이어야 합니다.")
    if any(not isinstance(row, list) for row in regions):
        raise PuzzleParseError("JSON의 'regions' 각 행은 배열이어야 합니다.")

    try:
        return Puzzle.from_region_grid(regions)
    except InvalidRegionMapError as error:
        # JSON 문법·스키마·모델 오류는 공개 파싱 예외를 공유하며 RnCn 등 상세 메시지를 보존한다.
        raise PuzzleParseError(str(error)) from error

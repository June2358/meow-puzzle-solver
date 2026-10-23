"""Parser for the canonical JSON Queens puzzle format."""

from __future__ import annotations

from puzzle_common.json_input import decode_json

from .model import InvalidRegionMapError, Puzzle


class PuzzleParseError(InvalidRegionMapError):
    """Raised when input cannot be interpreted as a puzzle document."""


def parse_puzzle_json(text: str) -> Puzzle:
    """Parse the canonical JSON puzzle object.

    The object has exactly one ``regions`` field containing a two-dimensional
    array of region-label strings. No metadata or solution fields are accepted.
    """

    document = decode_json(text, PuzzleParseError)

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
        # JSON syntax/schema/model failures share one public parse-error type,
        # while preserving the precise validation message (including RnCn).
        raise PuzzleParseError(str(error)) from error

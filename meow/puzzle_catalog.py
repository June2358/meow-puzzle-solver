"""Validated built-in MEOW presets stored as package resources."""

import json
from collections.abc import Mapping
from functools import cache
from importlib import resources
from types import MappingProxyType
from typing import Final

from .model import InvalidRegionMapError, Puzzle, RegionGrid

PRESET_NAMES: Final[tuple[str, ...]] = (
    "쉬움",
    "보통",
    "어려움",
    "전문가",
    "마스터",
    "극한",
)

type _PuzzleCatalog = Mapping[str, RegionGrid]


class PuzzleDataError(RuntimeError):
    """Raised when the packaged preset catalog is missing or malformed."""


def _validate_catalog(data: object) -> _PuzzleCatalog:
    if type(data) is not dict:
        raise PuzzleDataError("퍼즐 데이터의 최상위 값은 객체여야 합니다.")
    if set(data) != set(PRESET_NAMES):
        expected = ", ".join(PRESET_NAMES)
        raise PuzzleDataError(
            f"퍼즐 데이터에는 다음 여섯 프리셋이 필요합니다: {expected}"
        )

    validated: dict[str, RegionGrid] = {}
    for name in PRESET_NAMES:
        try:
            puzzle = Puzzle.from_region_grid(data[name])
        except InvalidRegionMapError as error:
            raise PuzzleDataError(
                f"프리셋 {name!r}의 영역 맵이 잘못되었습니다: {error}"
            ) from error
        validated[name] = puzzle.region_grid
    return MappingProxyType(validated)


@cache
def _load_puzzle_catalog() -> _PuzzleCatalog:
    """Load and validate the six packaged presets once."""

    try:
        text = (
            resources.files(__package__)
            .joinpath("puzzles.json")
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, OSError) as error:
        raise PuzzleDataError("패키지의 puzzles.json을 읽을 수 없습니다.") from error

    try:
        decoded = json.loads(text)
    except json.JSONDecodeError as error:
        raise PuzzleDataError(
            f"puzzles.json이 올바른 JSON이 아닙니다: {error.msg} "
            f"(줄 {error.lineno}, 열 {error.colno})"
        ) from error
    return _validate_catalog(decoded)


def load_preset(name: str) -> Puzzle:
    """Return one validated built-in puzzle by its canonical difficulty name."""

    if not isinstance(name, str):
        raise TypeError("프리셋 이름은 문자열이어야 합니다.")
    try:
        grid = _load_puzzle_catalog()[name]
    except KeyError as error:
        choices = ", ".join(PRESET_NAMES)
        raise ValueError(
            f"알 수 없는 프리셋 {name!r}입니다. 사용 가능: {choices}"
        ) from error
    return Puzzle.from_region_grid(grid)

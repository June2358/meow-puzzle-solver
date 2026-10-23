"""Validated built-in Sudoku presets."""

from collections.abc import Mapping
from functools import cache
from types import MappingProxyType

from puzzle_common.catalog import PuzzleDataError as PuzzleDataError
from puzzle_common.catalog import read_catalog

from .board import Grid, InvalidBoardError, Puzzle

type PuzzleCatalog = Mapping[str, Grid]


def _validate_catalog(data: object) -> PuzzleCatalog:
    if type(data) is not dict or not data:
        raise PuzzleDataError(
            "퍼즐 데이터의 최상위 값은 비어 있지 않은 객체여야 합니다."
        )

    validated: dict[str, Grid] = {}
    for difficulty, raw_grid in data.items():
        if type(difficulty) is not str or not difficulty.strip():
            raise PuzzleDataError("난이도 이름은 비어 있지 않은 문자열이어야 합니다.")
        try:
            puzzle = Puzzle(raw_grid)
        except InvalidBoardError as exc:
            raise PuzzleDataError(
                f"난이도 {difficulty!r}의 퍼즐이 잘못되었습니다: {exc}"
            ) from exc
        if not puzzle.givens:
            raise PuzzleDataError(
                f"난이도 {difficulty!r}의 퍼즐에는 초기 단서가 없습니다."
            )
        validated[difficulty] = puzzle.grid

    return MappingProxyType(validated)


@cache
def load_puzzle_catalog() -> PuzzleCatalog:
    """Load and validate the packaged preset catalog once."""

    return _validate_catalog(read_catalog(__package__))

"""Read packaged preset JSON while puzzle-specific validators own its schema."""

from collections.abc import Callable, Mapping
from functools import cache
from importlib import resources
from types import MappingProxyType

from .json_input import decode_json


class PuzzleDataError(RuntimeError):
    """Raised when the packaged preset catalog is missing or malformed."""


def read_catalog(package: str) -> object:
    try:
        text = (
            resources.files(package)
            .joinpath("puzzles.json")
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, OSError) as error:
        raise PuzzleDataError("패키지의 puzzles.json을 읽을 수 없습니다.") from error
    return decode_json(text, PuzzleDataError, "puzzles.json")


@cache
def load_catalog[T](package: str, validate: Callable[[object], T]) -> Mapping[str, T]:
    data = read_catalog(package)
    if type(data) is not dict or not data:
        raise PuzzleDataError(
            "퍼즐 데이터의 최상위 값은 비어 있지 않은 객체여야 합니다."
        )
    validated = {}
    for name, grid in data.items():
        if type(name) is not str or not name.strip():
            raise PuzzleDataError("난이도 이름은 비어 있지 않은 문자열이어야 합니다.")
        try:
            validated[name] = validate(grid)
        except ValueError as error:
            raise PuzzleDataError(
                f"난이도 {name!r}의 퍼즐이 잘못되었습니다: {error}"
            ) from error
    return MappingProxyType(validated)

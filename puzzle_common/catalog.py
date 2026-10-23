"""Read packaged preset JSON while puzzle-specific validators own its schema."""

from importlib import resources

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

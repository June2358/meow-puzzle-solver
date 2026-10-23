"""검증된 불변 스도쿠 퍼즐 모델."""

from collections.abc import Sequence
from dataclasses import dataclass, field

from .topology import CELLS, SIZE, UNITS, Cell

type Grid = tuple[tuple[int, ...], ...]


class InvalidBoardError(ValueError):
    """값이 올바른 9×9 스도쿠 격자가 아닐 때 발생한다."""


class InvalidPuzzleError(InvalidBoardError):
    """초기 단서가 스도쿠 규칙을 위반할 때 발생한다."""


def validate_grid(grid: object) -> Grid:
    """9×9 격자를 검증해 원본과 별칭을 공유하지 않는 불변 격자로 반환한다.

    값은 정확히 ``int``인 0~9만 허용하며 ``int``의 하위형인 ``bool``은 거부한다."""

    if isinstance(grid, (str, bytes)) or not isinstance(grid, Sequence):
        raise InvalidBoardError("보드는 9개 행으로 이루어진 시퀀스여야 합니다.")

    if len(grid) != SIZE:
        raise InvalidBoardError(
            f"보드는 정확히 {SIZE}개 행이어야 합니다: {len(grid)}개"
        )

    normalized_rows: list[tuple[int, ...]] = []
    for row_index, row in enumerate(grid):
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise InvalidBoardError(
                f"{row_index + 1}행은 {SIZE}개 정수로 이루어진 시퀀스여야 합니다."
            )
        if len(row) != SIZE:
            raise InvalidBoardError(
                f"{row_index + 1}행은 정확히 {SIZE}개 값이어야 합니다: {len(row)}개"
            )

        normalized_row: list[int] = []
        for col_index, value in enumerate(row):
            if type(value) is not int:
                raise InvalidBoardError(
                    f"R{row_index + 1}C{col_index + 1}은 정수여야 합니다."
                )
            if not 0 <= value <= SIZE:
                raise InvalidBoardError(
                    f"R{row_index + 1}C{col_index + 1}은 0~{SIZE}여야 합니다: {value}"
                )
            normalized_row.append(value)
        normalized_rows.append(tuple(normalized_row))

    return tuple(normalized_rows)


def _find_conflicts_in_valid_grid(grid: Grid) -> frozenset[Cell]:
    conflicts: set[Cell] = set()
    for unit in UNITS:
        cells_by_value: dict[int, list[Cell]] = {}
        for row, col in unit:
            value = grid[row][col]
            if value != 0:
                cells_by_value.setdefault(value, []).append((row, col))
        for cells in cells_by_value.values():
            if len(cells) > 1:
                conflicts.update(cells)
    return frozenset(conflicts)


def find_conflicting_cells(grid: object) -> frozenset[Cell]:
    """행·열·박스 충돌에 참여하는 모든 칸을 반환한다."""

    normalized = validate_grid(grid)
    return _find_conflicts_in_valid_grid(normalized)


@dataclass(frozen=True, slots=True)
class Puzzle:
    """유효한 초기 단서로 구성된 불변 스도쿠 퍼즐."""

    grid: Grid
    givens: frozenset[Cell] = field(init=False)

    def __init__(self, grid: object):
        normalized = validate_grid(grid)
        conflicts = _find_conflicts_in_valid_grid(normalized)
        if conflicts:
            first_row, first_col = min(conflicts)
            raise InvalidPuzzleError(
                "초기 단서가 행, 열 또는 박스에서 중복됩니다: "
                f"R{first_row + 1}C{first_col + 1}"
            )

        object.__setattr__(self, "grid", normalized)
        object.__setattr__(
            self,
            "givens",
            frozenset((row, col) for row, col in CELLS if normalized[row][col] != 0),
        )

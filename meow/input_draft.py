"""pygame 입력 화면용 미완성 불변 영역 격자 초안."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from .model import (
    MAX_PUZZLE_SIZE,
    Cell,
    InvalidRegionMapError,
    Puzzle,
    _normalize_region_label,
)

type DraftLabel = str | None
type DraftGrid = tuple[tuple[DraftLabel, ...], ...]


class InvalidDraftError(ValueError):
    """초안이 비어 있지 않은 정사각형 라벨 격자가 아닐 때 발생한다."""


class IncompleteDraftError(InvalidDraftError):
    """빈칸 때문에 초안을 Puzzle로 만들 수 없을 때 발생한다."""


def _normalize_label(label: object, row: int, column: int) -> DraftLabel:
    if label is None:
        return None
    try:
        return _normalize_region_label(label, row, column)
    except InvalidRegionMapError as error:
        raise InvalidDraftError(str(error)) from error


def _normalize_grid(value: object) -> DraftGrid:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise InvalidDraftError("draft는 행으로 이루어진 시퀀스여야 합니다.")
    if not value:
        raise InvalidDraftError("draft는 비어 있을 수 없습니다.")

    size = len(value)
    if size > MAX_PUZZLE_SIZE:
        raise InvalidDraftError(
            f"draft는 최대 {MAX_PUZZLE_SIZE}×{MAX_PUZZLE_SIZE}까지 지원합니다."
        )
    rows: list[tuple[DraftLabel, ...]] = []
    for row_index, row in enumerate(value):
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise InvalidDraftError(
                f"{row_index + 1}행은 {size}개 영역 이름의 시퀀스여야 합니다."
            )
        if len(row) != size:
            raise InvalidDraftError(
                f"draft는 {size}×{size} 정사각형이어야 합니다: "
                f"{row_index + 1}행은 {len(row)}칸"
            )
        rows.append(
            tuple(
                _normalize_label(label, row_index, column_index)
                for column_index, label in enumerate(row)
            )
        )
    return tuple(rows)


@dataclass(frozen=True, slots=True)
class RegionDraft:
    """빈칸을 허용하지만 잘못된 라벨은 허용하지 않는 정사각형 초안."""

    grid: DraftGrid
    size: int = field(init=False)

    def __init__(self, grid: object):
        normalized = _normalize_grid(grid)
        object.__setattr__(self, "grid", normalized)
        object.__setattr__(self, "size", len(normalized))

    @classmethod
    def empty(cls, size: int) -> RegionDraft:
        """빈 ``size`` × ``size`` 초안을 만든다."""

        if type(size) is not int or not 1 <= size <= MAX_PUZZLE_SIZE:
            raise InvalidDraftError(f"draft 크기는 1~{MAX_PUZZLE_SIZE}여야 합니다.")
        return cls(tuple(tuple(None for _ in range(size)) for _ in range(size)))

    @property
    def filled_count(self) -> int:
        return sum(label is not None for row in self.grid for label in row)

    @property
    def labels(self) -> tuple[str, ...]:
        """채워진 라벨을 행 우선의 첫 등장 순서로 반환한다."""

        return tuple(
            dict.fromkeys(
                label for row in self.grid for label in row if label is not None
            )
        )

    def validate_cell(self, cell: object) -> Cell:
        if (
            isinstance(cell, (str, bytes))
            or not isinstance(cell, Sequence)
            or len(cell) != 2
        ):
            raise TypeError("셀 좌표는 (행, 열) 쌍이어야 합니다.")
        row, column = cell
        if type(row) is not int or type(column) is not int:
            raise TypeError("행과 열 좌표는 정수여야 합니다.")
        if not 0 <= row < self.size or not 0 <= column < self.size:
            raise IndexError(f"draft 밖의 좌표입니다: ({row}, {column})")
        return row, column

    def label_at(self, cell: Cell) -> DraftLabel:
        row, column = self.validate_cell(cell)
        return self.grid[row][column]

    def with_cell(self, cell: Cell, label: DraftLabel) -> RegionDraft:
        """칸 하나를 변경한 새 초안을 반환한다."""

        row, column = self.validate_cell(cell)
        normalized = _normalize_label(label, row, column)
        if self.grid[row][column] == normalized:
            return self
        rows = [list(source_row) for source_row in self.grid]
        rows[row][column] = normalized
        return RegionDraft(rows)

    def first_empty(self) -> Cell | None:
        for row_index, row in enumerate(self.grid):
            for column_index, label in enumerate(row):
                if label is None:
                    return row_index, column_index
        return None

    def to_puzzle(self) -> Puzzle:
        """첫 빈칸 좌표를 먼저 검사한 뒤 Puzzle을 만든다."""

        empty = self.first_empty()
        if empty is not None:
            row, column = empty
            raise IncompleteDraftError(
                f"R{row + 1}C{column + 1}의 영역 라벨을 입력하세요."
            )
        return Puzzle.from_region_grid(self.grid)

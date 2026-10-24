"""Immutable puzzle definition and precomputed Queens topology."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal, overload

type Cell = tuple[int, int]
type Unit = tuple[Cell, ...]
type RegionGrid = tuple[tuple[str, ...], ...]
type DraftGrid = tuple[tuple[str | None, ...], ...]
MAX_PUZZLE_SIZE = 26


class InvalidRegionMapError(ValueError):
    """Raised when a value is not a valid square Queens region map."""


def _normalize_region_label(label: object, row: int, column: int) -> str:
    if not isinstance(label, str) or not label.strip():
        raise InvalidRegionMapError(
            f"R{row + 1}C{column + 1}의 영역 이름은 비어 있지 않은 문자열이어야 합니다."
        )
    if label != label.strip():
        raise InvalidRegionMapError(
            f"R{row + 1}C{column + 1}의 영역 이름에는 앞뒤 공백을 사용할 수 없습니다."
        )
    if chr(0) in label or any(0xD800 <= ord(char) <= 0xDFFF for char in label):
        raise InvalidRegionMapError(
            f"R{row + 1}C{column + 1}의 영역 이름에는 화면에 표시할 수 없는 문자를 "
            "사용할 수 없습니다."
        )
    return label


@overload
def _normalize_region_grid(
    value: object, *, allow_empty: Literal[False] = False
) -> RegionGrid: ...


@overload
def _normalize_region_grid(
    value: object, *, allow_empty: Literal[True]
) -> DraftGrid: ...


def _normalize_region_grid(value: object, *, allow_empty: bool = False) -> DraftGrid:
    subject = "draft는" if allow_empty else "영역 맵은"
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise InvalidRegionMapError(f"{subject} 행으로 이루어진 시퀀스여야 합니다.")
    if not value:
        raise InvalidRegionMapError(f"{subject} 비어 있을 수 없습니다.")

    size = len(value)
    if size > MAX_PUZZLE_SIZE:
        raise InvalidRegionMapError(
            f"{subject} 최대 {MAX_PUZZLE_SIZE}×{MAX_PUZZLE_SIZE}까지 지원합니다."
        )
    rows: list[tuple[str | None, ...]] = []
    for row_index, row in enumerate(value):
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise InvalidRegionMapError(
                f"{row_index + 1}행은 {size}개 영역 이름의 시퀀스여야 합니다."
            )
        if len(row) != size:
            raise InvalidRegionMapError(
                f"{subject} {size}×{size} 정사각형이어야 합니다: "
                f"{row_index + 1}행은 {len(row)}칸"
            )

        normalized_row: list[str | None] = []
        for col_index, label in enumerate(row):
            normalized_row.append(
                None
                if allow_empty and label is None
                else _normalize_region_label(label, row_index, col_index)
            )
        rows.append(tuple(normalized_row))

    return tuple(rows)


def normalize_draft(grid: object) -> DraftGrid:
    """Validate a region-grid draft while retaining empty cells."""

    return _normalize_region_grid(grid, allow_empty=True)


def create_puzzle(grid: object) -> Puzzle:
    """Construct a puzzle, reporting the first unfilled draft coordinate."""

    normalized = normalize_draft(grid)
    for row_index, row in enumerate(normalized):
        for column_index, label in enumerate(row):
            if label is None:
                raise InvalidRegionMapError(
                    f"R{row_index + 1}C{column_index + 1}의 영역 라벨을 입력하세요."
                )
    return Puzzle(normalized)


def _ordered_labels(grid: RegionGrid) -> tuple[str, ...]:
    # dict insertion order gives a stable row-major region order.
    return tuple(dict.fromkeys(label for row in grid for label in row))


@dataclass(frozen=True, slots=True, eq=False)
class Puzzle:
    """An immutable N×N Queens puzzle with all topology precomputed.

    Coordinates are zero-based ``(row, column)`` tuples. Region indices use
    the stable row-major order in which their labels first appear.
    """

    region_grid: RegionGrid
    size: int = field(init=False)
    region_labels: tuple[str, ...] = field(init=False)
    cells: Unit = field(init=False)
    rows: tuple[Unit, ...] = field(init=False)
    cols: tuple[Unit, ...] = field(init=False)
    regions: tuple[Unit, ...] = field(init=False)
    units: tuple[Unit, ...] = field(init=False)
    conflicts: Mapping[Cell, frozenset[Cell]] = field(init=False, repr=False)
    _region_index_by_cell: Mapping[Cell, int] = field(init=False, repr=False)

    def __init__(self, region_grid: object):
        grid = _normalize_region_grid(region_grid)
        size = len(grid)
        labels = _ordered_labels(grid)
        if len(labels) != size:
            raise InvalidRegionMapError(
                f"{size}×{size} 영역 맵에는 정확히 {size}개 영역이 있어야 합니다: "
                f"{len(labels)}개"
            )
        cells: Unit = tuple((row, col) for row in range(size) for col in range(size))
        rows: tuple[Unit, ...] = tuple(
            tuple((row, col) for col in range(size)) for row in range(size)
        )
        cols: tuple[Unit, ...] = tuple(
            tuple((row, col) for row in range(size)) for col in range(size)
        )

        label_indices = {label: index for index, label in enumerate(labels)}
        region_index_by_cell = {
            cell: label_indices[grid[cell[0]][cell[1]]] for cell in cells
        }
        regions: tuple[Unit, ...] = tuple(
            tuple(cell for cell in cells if region_index_by_cell[cell] == index)
            for index in range(size)
        )
        units = rows + cols + regions
        conflicts: dict[Cell, frozenset[Cell]] = {}
        for cell in cells:
            row, col = cell
            peers = set(rows[row]) | set(cols[col])
            peers.update(regions[region_index_by_cell[cell]])
            for adjacent_row in range(max(0, row - 1), min(size, row + 2)):
                for adjacent_col in range(max(0, col - 1), min(size, col + 2)):
                    peers.add((adjacent_row, adjacent_col))
            peers.discard(cell)
            conflicts[cell] = frozenset(peers)

        object.__setattr__(self, "region_grid", grid)
        object.__setattr__(self, "size", size)
        object.__setattr__(self, "region_labels", labels)
        object.__setattr__(self, "cells", cells)
        object.__setattr__(self, "rows", rows)
        object.__setattr__(self, "cols", cols)
        object.__setattr__(self, "regions", regions)
        object.__setattr__(self, "units", units)
        object.__setattr__(self, "conflicts", MappingProxyType(conflicts))
        object.__setattr__(
            self,
            "_region_index_by_cell",
            MappingProxyType(region_index_by_cell),
        )

    @classmethod
    def from_region_grid(cls, region_grid: object) -> Puzzle:
        """Validate a region grid and construct its immutable puzzle."""

        return cls(region_grid)

    def validate_cell(self, cell: object) -> Cell:
        """Return a normalized cell or raise for an invalid coordinate."""

        if (
            isinstance(cell, (str, bytes))
            or not isinstance(cell, Sequence)
            or len(cell) != 2
        ):
            raise TypeError("셀 좌표는 (행, 열) 쌍이어야 합니다.")
        row, col = cell
        if type(row) is not int or type(col) is not int:
            raise TypeError("행과 열 좌표는 정수여야 합니다.")
        if not 0 <= row < self.size or not 0 <= col < self.size:
            raise IndexError(f"영역 맵 밖의 좌표입니다: ({row}, {col})")
        return row, col

    def region_of(self, cell: Cell) -> int:
        """Return the zero-based stable region index containing ``cell``."""

        return self._region_index_by_cell[self.validate_cell(cell)]

    def region_label(self, cell: Cell) -> str:
        """Return the original region label at ``cell``."""

        normalized = self.validate_cell(cell)
        return self.region_grid[normalized[0]][normalized[1]]

    def conflict(self, first: Cell, second: Cell) -> bool:
        """Whether two distinct cells cannot both contain cats."""

        normalized_first = self.validate_cell(first)
        normalized_second = self.validate_cell(second)
        return normalized_second in self.conflicts[normalized_first]

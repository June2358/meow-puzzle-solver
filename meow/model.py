"""불변 퍼즐 정의와 미리 계산된 Queens 칸 관계."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

type Cell = tuple[int, int]
type Unit = tuple[Cell, ...]
type RegionGrid = tuple[tuple[str, ...], ...]
MAX_PUZZLE_SIZE = 26


class InvalidRegionMapError(ValueError):
    """값이 유효한 정사각형 Queens 영역 맵이 아닐 때 발생한다."""


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


def _normalize_region_grid(value: object) -> RegionGrid:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise InvalidRegionMapError("영역 맵은 행으로 이루어진 시퀀스여야 합니다.")
    if not value:
        raise InvalidRegionMapError("영역 맵은 비어 있을 수 없습니다.")

    size = len(value)
    if size > MAX_PUZZLE_SIZE:
        raise InvalidRegionMapError(
            f"영역 맵은 최대 {MAX_PUZZLE_SIZE}×{MAX_PUZZLE_SIZE}까지 지원합니다."
        )
    rows: list[tuple[str, ...]] = []
    for row_index, row in enumerate(value):
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise InvalidRegionMapError(
                f"{row_index + 1}행은 {size}개 영역 이름의 시퀀스여야 합니다."
            )
        if len(row) != size:
            raise InvalidRegionMapError(
                f"영역 맵은 {size}×{size} 정사각형이어야 합니다: "
                f"{row_index + 1}행은 {len(row)}칸"
            )

        normalized_row: list[str] = []
        for col_index, label in enumerate(row):
            normalized_row.append(_normalize_region_label(label, row_index, col_index))
        rows.append(tuple(normalized_row))

    return tuple(rows)


def _ordered_labels(grid: RegionGrid) -> tuple[str, ...]:
    # dict 삽입 순서로 행 우선의 고정된 영역 순서를 얻는다.
    return tuple(dict.fromkeys(label for row in grid for label in row))


@dataclass(frozen=True, slots=True, eq=False)
class Puzzle:
    """모든 칸 관계를 미리 계산한 불변 N×N Queens 퍼즐.

    좌표는 0부터 시작하는 ``(row, column)`` 튜플이다. 영역 인덱스는
    라벨이 처음 나타나는 행 우선 순서로 고정한다."""

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
        """영역 격자를 검증하고 불변 퍼즐을 만든다."""

        return cls(region_grid)

    def validate_cell(self, cell: object) -> Cell:
        """정규화된 칸을 반환하고 잘못된 좌표에는 예외를 발생시킨다."""

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
        """``cell``이 속한 영역의 0부터 시작하는 고정 인덱스를 반환한다."""

        return self._region_index_by_cell[self.validate_cell(cell)]

    def region_label(self, cell: Cell) -> str:
        """``cell``의 원래 영역 라벨을 반환한다."""

        normalized = self.validate_cell(cell)
        return self.region_grid[normalized[0]][normalized[1]]

    def conflict(self, first: Cell, second: Cell) -> bool:
        """서로 다른 두 칸에 고양이를 동시에 놓을 수 없는지 검사한다."""

        normalized_first = self.validate_cell(first)
        normalized_second = self.validate_cell(second)
        return normalized_second in self.conflicts[normalized_first]

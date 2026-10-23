"""가변 논리 보드 상태와 불변 finder 스냅샷."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum

from .model import Cell, Puzzle


class CellState(StrEnum):
    """논리 엔진에서 사용하는 세 가지 상태."""

    POSSIBLE = "possible"
    EXCLUDED = "excluded"
    CAT = "cat"


type StatusGrid = tuple[tuple[CellState, ...], ...]


class InvalidStateTransitionError(ValueError):
    """요청한 상태 변경이 현재 정보와 모순일 때 발생한다."""


def _normalize_status_grid(puzzle: Puzzle, value: object) -> StatusGrid:
    if not isinstance(value, (tuple, list)) or len(value) != puzzle.size:
        raise ValueError(f"상태에는 정확히 {puzzle.size}개 행이 있어야 합니다.")

    rows: list[tuple[CellState, ...]] = []
    for row_index, row in enumerate(value):
        if not isinstance(row, (tuple, list)) or len(row) != puzzle.size:
            raise ValueError(
                f"상태의 {row_index + 1}행에는 정확히 "
                f"{puzzle.size}개 셀이 있어야 합니다."
            )
        if any(not isinstance(status, CellState) for status in row):
            raise TypeError("모든 셀 상태는 CellState여야 합니다.")
        rows.append(tuple(row))
    return tuple(rows)


def _cells_with(
    puzzle: Puzzle,
    grid: StatusGrid | list[list[CellState]],
    status: CellState,
) -> tuple[Cell, ...]:
    return tuple(cell for cell in puzzle.cells if grid[cell[0]][cell[1]] == status)


def _filter_unit(
    puzzle: Puzzle,
    grid: StatusGrid | list[list[CellState]],
    unit: Iterable[Cell],
    status: CellState,
) -> tuple[Cell, ...]:
    if isinstance(unit, (str, bytes)):
        raise TypeError("unit은 셀 좌표의 iterable이어야 합니다.")
    cells: list[Cell] = []
    for raw_cell in unit:
        cell = puzzle.validate_cell(raw_cell)
        if grid[cell[0]][cell[1]] == status:
            cells.append(cell)
    return tuple(cells)


@dataclass(frozen=True, slots=True)
class LogicSnapshot:
    """추론 finder에 안전하게 전달할 수 있는 불변 보드 상태."""

    puzzle: Puzzle
    status_grid: StatusGrid

    def __post_init__(self) -> None:
        if not isinstance(self.puzzle, Puzzle):
            raise TypeError("LogicSnapshot은 Puzzle을 필요로 합니다.")
        object.__setattr__(
            self,
            "status_grid",
            _normalize_status_grid(self.puzzle, self.status_grid),
        )

    @property
    def possible_cells(self) -> tuple[Cell, ...]:
        return _cells_with(self.puzzle, self.status_grid, CellState.POSSIBLE)

    @property
    def cats(self) -> frozenset[Cell]:
        return frozenset(_cells_with(self.puzzle, self.status_grid, CellState.CAT))

    def status_at(self, cell: Cell) -> CellState:
        row, col = self.puzzle.validate_cell(cell)
        return self.status_grid[row][col]

    def is_possible(self, cell: Cell) -> bool:
        return self.status_at(cell) is CellState.POSSIBLE

    def is_excluded(self, cell: Cell) -> bool:
        return self.status_at(cell) is CellState.EXCLUDED

    def is_cat(self, cell: Cell) -> bool:
        return self.status_at(cell) is CellState.CAT

    def candidates_for(self, unit: Iterable[Cell]) -> tuple[Cell, ...]:
        return _filter_unit(self.puzzle, self.status_grid, unit, CellState.POSSIBLE)

    def cats_in(self, unit: Iterable[Cell]) -> tuple[Cell, ...]:
        return _filter_unit(self.puzzle, self.status_grid, unit, CellState.CAT)

    def has_contradiction(self) -> bool:
        cats = self.cats
        return any(self.puzzle.conflicts[cell] & cats for cell in cats) or any(
            not self.cats_in(unit) and not self.candidates_for(unit)
            for unit in self.puzzle.units
        )

    def is_solved(self) -> bool:
        cats = self.cats
        # 충돌하지 않는 고양이 N마리는 N개 행·열·영역을 모두 채운다.
        return len(cats) == self.puzzle.size and not any(
            self.puzzle.conflicts[cell] & cats for cell in cats
        )


class LogicState:
    """명시적인 기본 연산으로만 변경하는 가변 칸 상태."""

    __slots__ = ("puzzle", "_statuses")

    def __init__(self, puzzle: Puzzle):
        if not isinstance(puzzle, Puzzle):
            raise TypeError("LogicState는 Puzzle에서 생성해야 합니다.")
        self.puzzle = puzzle
        self._statuses = [
            [CellState.POSSIBLE for _ in range(puzzle.size)] for _ in range(puzzle.size)
        ]

    @classmethod
    def from_snapshot(cls, snapshot: LogicSnapshot) -> LogicState:
        if not isinstance(snapshot, LogicSnapshot):
            raise TypeError("LogicState.from_snapshot은 LogicSnapshot을 필요로 합니다.")
        state = cls(snapshot.puzzle)
        state._statuses = [list(row) for row in snapshot.status_grid]
        return state

    @property
    def status_grid(self) -> StatusGrid:
        return tuple(tuple(row) for row in self._statuses)

    def exclude(self, cell: Cell) -> bool:
        """가능한 칸을 제외하고 상태 변경 여부를 반환한다."""

        row, col = self.puzzle.validate_cell(cell)
        current = self._statuses[row][col]
        if current is CellState.EXCLUDED:
            return False
        if current is CellState.CAT:
            raise InvalidStateTransitionError(
                f"R{row + 1}C{col + 1}에는 이미 고양이가 있습니다."
            )
        self._statuses[row][col] = CellState.EXCLUDED
        return True

    def place_cat(self, cell: Cell) -> bool:
        """암묵적인 전파 없이 고양이를 놓고 변경 여부를 반환한다."""

        row, col = normalized = self.puzzle.validate_cell(cell)
        current = self._statuses[row][col]
        if current is CellState.CAT:
            return False
        if current is CellState.EXCLUDED:
            raise InvalidStateTransitionError(
                f"제외된 R{row + 1}C{col + 1}에는 고양이를 놓을 수 없습니다."
            )

        cats = frozenset(_cells_with(self.puzzle, self._statuses, CellState.CAT))
        conflicting_cats = cats & self.puzzle.conflicts[normalized]
        if conflicting_cats:
            other_row, other_col = min(conflicting_cats)
            raise InvalidStateTransitionError(
                f"R{row + 1}C{col + 1}은 이미 놓인 "
                f"R{other_row + 1}C{other_col + 1}과 충돌합니다."
            )

        self._statuses[row][col] = CellState.CAT
        return True

    def snapshot(self) -> LogicSnapshot:
        return LogicSnapshot(self.puzzle, self.status_grid)

    def clone(self) -> LogicState:
        clone = type(self)(self.puzzle)
        clone._statuses = [row[:] for row in self._statuses]
        return clone

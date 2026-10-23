"""Mutable values and candidates used internally while solving."""

from collections.abc import Iterable

from .board import Grid, Puzzle
from .solve_types import CandidateGrid, ContradictionKind, ContradictionWitness
from .topology import CELLS, DIGITS, PEERS, SIZE, UNITS, Cell


def _validate_cell(cell: object) -> Cell:
    if (
        not isinstance(cell, tuple)
        or len(cell) != 2
        or type(cell[0]) is not int
        or type(cell[1]) is not int
    ):
        raise TypeError("셀 좌표는 (행, 열) 정수 튜플이어야 합니다.")

    row, col = cell
    if not 0 <= row < SIZE or not 0 <= col < SIZE:
        raise IndexError(f"잘못된 좌표입니다: {cell}")
    return row, col


def _validate_digit(value: object) -> int:
    if type(value) is not int or not 1 <= value <= SIZE:
        raise ValueError(f"설정 값은 1~{SIZE} 정수여야 합니다: {value!r}")
    return value


def _validate_digits(values: object) -> frozenset[int]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Iterable):
        raise TypeError("후보 값은 1~9 정수의 iterable이어야 합니다.")
    return frozenset(_validate_digit(value) for value in values)


class SolverState:
    """Mutable Sudoku values and candidates with controlled state changes."""

    __slots__ = ("_candidates", "_values")

    def __init__(self, puzzle: Puzzle):
        if not isinstance(puzzle, Puzzle):
            raise TypeError("SolverState는 Puzzle에서 생성해야 합니다.")

        self._values = [list(row) for row in puzzle.grid]
        self._candidates = [
            [self._initial_candidates((row, col)) for col in range(SIZE)]
            for row in range(SIZE)
        ]

    def _initial_candidates(self, cell: Cell) -> set[int]:
        row, col = cell
        value = self._values[row][col]
        if value != 0:
            return {value}

        peer_values = {
            self._values[peer_row][peer_col]
            for peer_row, peer_col in PEERS[cell]
            if self._values[peer_row][peer_col] != 0
        }
        return set(DIGITS - peer_values)

    def clone(self) -> "SolverState":
        clone = object.__new__(type(self))
        clone._values = [row[:] for row in self._values]
        clone._candidates = [
            [cell_candidates.copy() for cell_candidates in row]
            for row in self._candidates
        ]
        return clone

    def value_at(self, cell: Cell) -> int:
        row, col = _validate_cell(cell)
        return self._values[row][col]

    def to_grid(self) -> Grid:
        return tuple(tuple(row) for row in self._values)

    def candidates_at(self, cell: Cell) -> frozenset[int]:
        row, col = _validate_cell(cell)
        return frozenset(self._candidates[row][col])

    def candidate_grid(self) -> CandidateGrid:
        return tuple(
            tuple(frozenset(cell_candidates) for cell_candidates in row)
            for row in self._candidates
        )

    def set_value(self, cell: Cell, value: int) -> bool:
        """Assign a candidate value and propagate it to all peers."""

        row, col = _validate_cell(cell)
        value = _validate_digit(value)

        if self._values[row][col] != 0:
            return False
        if value not in self._candidates[row][col]:
            return False

        self._values[row][col] = value
        self._candidates[row][col] = {value}
        for peer_row, peer_col in PEERS[cell]:
            if self._values[peer_row][peer_col] == 0:
                self._candidates[peer_row][peer_col].discard(value)
        return True

    def remove_candidates(self, cell: Cell, values: Iterable[int]) -> frozenset[int]:
        """Remove candidates and return the values that actually changed."""

        row, col = _validate_cell(cell)
        values_to_remove = _validate_digits(values)
        if self._values[row][col] != 0:
            return frozenset()

        removed = self._candidates[row][col] & values_to_remove
        self._candidates[row][col].difference_update(values_to_remove)
        return frozenset(removed)

    def empty_cells(self) -> tuple[Cell, ...]:
        return tuple((row, col) for row, col in CELLS if self._values[row][col] == 0)

    def find_contradiction(self) -> ContradictionWitness | None:
        """Return the first contradiction in stable, simplest-first order."""

        for row, col in CELLS:
            if self._values[row][col] == 0 and not self._candidates[row][col]:
                return ContradictionWitness(
                    kind=ContradictionKind.EMPTY_CELL,
                    cells=((row, col),),
                )

        for unit_index, unit in enumerate(UNITS):
            possible_values: set[int] = set()
            for row, col in unit:
                value = self._values[row][col]
                if value:
                    possible_values.add(value)
                else:
                    possible_values.update(self._candidates[row][col])
            missing_values = DIGITS - possible_values
            if missing_values:
                return ContradictionWitness(
                    kind=ContradictionKind.MISSING_DIGIT,
                    unit_index=unit_index,
                    digits=frozenset({min(missing_values)}),
                )
        return None

    def is_complete(self) -> bool:
        return not self.empty_cells() and self.find_contradiction() is None

"""9x9 Sudoku topology shared by the model and solving techniques."""

from types import MappingProxyType
from typing import Final

SIZE: Final = 9
BOX_SIZE: Final = 3
DIGITS: Final = frozenset(range(1, SIZE + 1))

type Cell = tuple[int, int]
type Unit = tuple[Cell, ...]

CELLS: Final[tuple[Cell, ...]] = tuple(
    (row, col) for row in range(SIZE) for col in range(SIZE)
)
ROWS: Final[tuple[Unit, ...]] = tuple(
    tuple((row, col) for col in range(SIZE)) for row in range(SIZE)
)
COLS: Final[tuple[Unit, ...]] = tuple(
    tuple((row, col) for row in range(SIZE)) for col in range(SIZE)
)
BOXES: Final[tuple[Unit, ...]] = tuple(
    tuple(
        (row, col)
        for row in range(box_row, box_row + BOX_SIZE)
        for col in range(box_col, box_col + BOX_SIZE)
    )
    for box_row in range(0, SIZE, BOX_SIZE)
    for box_col in range(0, SIZE, BOX_SIZE)
)
UNITS: Final[tuple[Unit, ...]] = ROWS + COLS + BOXES

_units_by_cell = {cell: tuple(unit for unit in UNITS if cell in unit) for cell in CELLS}

_peers = {
    cell: frozenset(
        peer for unit in _units_by_cell[cell] for peer in unit if peer != cell
    )
    for cell in CELLS
}
PEERS: Final = MappingProxyType(_peers)

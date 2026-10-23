"""Puzzle-independent cell labels, without graphics dependencies."""


def cell_name(cell: tuple[int, int]) -> str:
    row, column = cell
    return f"R{row + 1}C{column + 1}"

"""Sudoku font sizes and board drawing helpers."""

from collections.abc import Collection

import pygame

from puzzle_common.ui_style import GRID_BOX_LINE, GRID_LINE, RED, Fonts, draw_grid_lines
from puzzle_common.ui_style import get_fonts as load_fonts

from .topology import BOX_SIZE, SIZE, Cell


def get_fonts() -> Fonts:
    return load_fonts(number_size=38, candidate_size=15)


def draw_sudoku_grid_lines(
    screen: pygame.Surface,
    origin: tuple[int, int],
    cell_size: int,
    *,
    thick_width: int = 3,
    thin_width: int = 1,
) -> None:
    """Draw a 9x9 grid with heavier box boundaries."""

    draw_grid_lines(screen, origin, cell_size, SIZE, color=GRID_LINE, width=thin_width)
    draw_grid_lines(
        screen,
        origin,
        cell_size * BOX_SIZE,
        SIZE // BOX_SIZE,
        color=GRID_BOX_LINE,
        width=thick_width,
    )


def draw_conflict_cells(
    screen: pygame.Surface,
    conflicts: Collection[Cell],
    origin: tuple[int, int],
    cell_size: int,
    *,
    alpha: int = 128,
) -> None:
    """Fill every conflicting cell with translucent red."""

    if not conflicts:
        return

    start_x, start_y = origin
    cell_surface = pygame.Surface((cell_size - 2, cell_size - 2))
    cell_surface.set_alpha(alpha)
    cell_surface.fill(RED)

    for row, col in conflicts:
        x = start_x + col * cell_size
        y = start_y + row * cell_size
        screen.blit(cell_surface, (x + 1, y + 1))

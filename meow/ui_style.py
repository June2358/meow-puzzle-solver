"""MEOW font sizes and colored-region drawing helpers."""

from __future__ import annotations

import colorsys
from functools import cache

import pygame

from puzzle_common.ui_style import (
    GRID_LINE,
    GRID_REGION_LINE,
    Color,
    Fonts,
    draw_grid_lines,
)
from puzzle_common.ui_style import get_fonts as load_fonts

from .model import RegionGrid


def get_fonts() -> Fonts:
    return load_fonts(number_size=34, candidate_size=13)


@cache
def region_palette(labels: tuple[str, ...]) -> dict[str, Color]:
    """Return stable, distinct pastel colors for an arbitrary region count."""

    palette: dict[str, Color] = {}
    for index, label in enumerate(labels):
        hue = ((index * 137.508) + 8.0) % 360.0
        saturation = 0.25 + (index % 3) * 0.035
        value = 0.97 - (index % 2) * 0.025
        red, green, blue = colorsys.hsv_to_rgb(hue / 360.0, saturation, value)
        palette[label] = (
            round(red * 255),
            round(green * 255),
            round(blue * 255),
        )
    return palette


def draw_region_grid_lines(
    screen: pygame.Surface,
    region_grid: RegionGrid,
    origin: tuple[int, int],
    cell_size: int,
    *,
    region_width: int = 3,
    cell_width: int = 1,
) -> None:
    """Draw thin cell lines and thick boundaries between colored regions."""

    if cell_size <= 0:
        raise ValueError("셀 크기는 양수여야 합니다.")
    size = len(region_grid)
    start_x, start_y = origin
    draw_grid_lines(screen, origin, cell_size, size, color=GRID_LINE, width=cell_width)

    for row in range(size):
        y1 = start_y + row * cell_size
        y2 = y1 + cell_size
        for boundary in range(size + 1):
            if (
                boundary in (0, size)
                or region_grid[row][boundary - 1] != region_grid[row][boundary]
            ):
                x = start_x + boundary * cell_size
                pygame.draw.line(
                    screen,
                    GRID_REGION_LINE,
                    (x, y1),
                    (x, y2),
                    region_width,
                )

    for column in range(size):
        x1 = start_x + column * cell_size
        x2 = x1 + cell_size
        for boundary in range(size + 1):
            if (
                boundary in (0, size)
                or region_grid[boundary - 1][column] != region_grid[boundary][column]
            ):
                y = start_y + boundary * cell_size
                pygame.draw.line(
                    screen,
                    GRID_REGION_LINE,
                    (x1, y),
                    (x2, y),
                    region_width,
                )

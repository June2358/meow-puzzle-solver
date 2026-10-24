"""The single renderer for immutable puzzle board projections."""

import colorsys
from functools import cache

import pygame

from .layout import BoardLayout
from .ui_style import (
    ACCENT_YELLOW,
    ACCENT_YELLOW_LIGHT,
    GRID_LINE,
    GRID_REGION_LINE,
    WHITE,
    Color,
    Fonts,
    draw_grid_lines,
)
from .view import BoardView, Cell


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


def _draw_cat(
    screen: pygame.Surface,
    rect: pygame.Rect,
    color: Color,
) -> None:
    """Draw a scalable cat face without depending on an external image asset."""

    size = min(rect.width, rect.height)
    center_x, center_y = rect.center
    if size < 18:
        radius = max(2, size // 4)
        pygame.draw.circle(screen, color, rect.center, radius)
        pygame.draw.polygon(
            screen,
            color,
            (
                (center_x - radius, center_y - radius // 2),
                (center_x - radius, center_y - radius * 2),
                (center_x, center_y - radius),
            ),
        )
        pygame.draw.polygon(
            screen,
            color,
            (
                (center_x + radius, center_y - radius // 2),
                (center_x + radius, center_y - radius * 2),
                (center_x, center_y - radius),
            ),
        )
        return

    radius = max(5, round(size * 0.27))
    head_y = center_y + round(size * 0.04)
    ear_height = max(4, round(size * 0.23))
    ear_spread = max(4, round(size * 0.2))
    pygame.draw.polygon(
        screen,
        color,
        (
            (center_x - radius + 2, head_y - radius // 2),
            (center_x - ear_spread, head_y - radius - ear_height),
            (center_x - 1, head_y - radius + 2),
        ),
    )
    pygame.draw.polygon(
        screen,
        color,
        (
            (center_x + radius - 2, head_y - radius // 2),
            (center_x + ear_spread, head_y - radius - ear_height),
            (center_x + 1, head_y - radius + 2),
        ),
    )
    pygame.draw.circle(screen, color, (center_x, head_y), radius)

    face = WHITE
    eye_y = head_y - radius // 5
    eye_offset = max(2, radius // 3)
    eye_radius = max(1, radius // 8)
    pygame.draw.circle(screen, face, (center_x - eye_offset, eye_y), eye_radius)
    pygame.draw.circle(screen, face, (center_x + eye_offset, eye_y), eye_radius)
    nose_y = head_y + radius // 5
    pygame.draw.polygon(
        screen,
        (244, 114, 182),
        (
            (center_x - 2, nose_y),
            (center_x + 2, nose_y),
            (center_x, nose_y + 3),
        ),
    )
    whisker_length = max(4, radius // 2)
    for offset in (-2, 2):
        y = nose_y + offset
        pygame.draw.line(
            screen,
            face,
            (center_x - 3, y),
            (center_x - 3 - whisker_length, y + offset // 2),
            1,
        )
        pygame.draw.line(
            screen,
            face,
            (center_x + 3, y),
            (center_x + 3 + whisker_length, y + offset // 2),
            1,
        )


def _draw_x(screen: pygame.Surface, rect: pygame.Rect, color: Color) -> None:
    padding = max(2, rect.width // 5)
    width = max(1, rect.width // 13)
    pygame.draw.line(
        screen,
        color,
        (rect.left + padding, rect.top + padding),
        (rect.right - padding, rect.bottom - padding),
        width,
    )
    pygame.draw.line(
        screen,
        color,
        (rect.right - padding, rect.top + padding),
        (rect.left + padding, rect.bottom - padding),
        width,
    )


def _fit_text(text: str, font: pygame.font.Font, width: int) -> str:
    if len(text) == 1 or font.size(text)[0] <= width:
        return text
    low, high = 0, len(text)
    while low < high:
        middle = (low + high + 1) // 2
        if font.size(text[:middle] + "…")[0] <= width:
            low = middle
        else:
            high = middle - 1
    return text[:low] + "…" if low else ""


def draw_board(
    screen: pygame.Surface,
    layout: BoardLayout,
    view: BoardView,
    fonts: Fonts,
    selected_cell: Cell | None = None,
) -> None:
    """Draw cells, fixed marks, highlights and boundaries from display data."""
    if layout.board_rect.size != (view.size * layout.cell_size,) * 2:
        raise ValueError("보드 표시와 레이아웃 크기가 일치해야 합니다.")
    for row_index, row in enumerate(view.cells):
        for column, cell in enumerate(row):
            rect = layout.cell_rect((row_index, column))
            pygame.draw.rect(screen, cell.background, rect)
            for color in cell.highlights:
                overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
                overlay.fill(color)
                screen.blit(overlay, rect.topleft)
            for mark in cell.marks:
                mark_rect = rect
                if mark.slot is not None:
                    mark_row, mark_column = divmod(mark.slot, 3)
                    mark_rect = pygame.Rect(
                        rect.left + mark_column * rect.width // 3,
                        rect.top + mark_row * rect.height // 3,
                        rect.width // 3,
                        rect.height // 3,
                    )
                if mark.kind == "cat":
                    _draw_cat(screen, mark_rect, mark.color)
                elif mark.kind == "cross":
                    _draw_x(screen, mark_rect, mark.color)
                elif mark.text:
                    font = (
                        fonts.candidate
                        if mark.slot is not None
                        or fonts.number.get_height() > mark_rect.height - 4
                        else fonts.number
                    )
                    text = _fit_text(mark.text, font, max(1, mark_rect.width - 5))
                    if not font.size(text)[0]:
                        continue
                    rendered = font.render(text, True, mark.color)
                    width, height = rendered.get_size()
                    scale = min(
                        1,
                        max(1, mark_rect.width - 5) / max(1, width),
                        max(1, mark_rect.height - 4) / max(1, height),
                    )
                    if scale < 1:
                        rendered = pygame.transform.smoothscale(
                            rendered,
                            (
                                max(1, round(width * scale)),
                                max(1, round(height * scale)),
                            ),
                        )
                    screen.blit(rendered, rendered.get_rect(center=mark_rect.center))
                if mark.struck:
                    half_width = min(5, max(1, mark_rect.width // 2 - 1))
                    x, y = mark_rect.center
                    pygame.draw.line(
                        screen, mark.color, (x - half_width, y), (x + half_width, y)
                    )
            if cell.outline is not None:
                pygame.draw.rect(screen, cell.outline, rect.inflate(-4, -4), width=3)
    draw_grid_lines(
        screen,
        layout.board_rect.topleft,
        layout.cell_size,
        view.size,
        color=GRID_LINE,
        width=1,
    )
    width = max(2, min(4, layout.cell_size // 12))
    for row in range(view.size):
        for boundary in range(view.size + 1):
            if (
                boundary in (0, view.size)
                or view.regions[row][boundary - 1] != view.regions[row][boundary]
            ):
                x = layout.board_rect.left + boundary * layout.cell_size
                y = layout.board_rect.top + row * layout.cell_size
                pygame.draw.line(
                    screen, GRID_REGION_LINE, (x, y), (x, y + layout.cell_size), width
                )
    for column in range(view.size):
        for boundary in range(view.size + 1):
            if (
                boundary in (0, view.size)
                or view.regions[boundary - 1][column] != view.regions[boundary][column]
            ):
                x = layout.board_rect.left + column * layout.cell_size
                y = layout.board_rect.top + boundary * layout.cell_size
                pygame.draw.line(
                    screen, GRID_REGION_LINE, (x, y), (x + layout.cell_size, y), width
                )
    if selected_cell is not None:
        row, column = selected_cell
        if not 0 <= row < view.size or not 0 <= column < view.size:
            raise ValueError("선택한 셀이 보드 밖에 있습니다.")
        rect = layout.cell_rect(selected_cell).inflate(-4, -4)
        overlay = pygame.Surface(rect.size, pygame.SRCALPHA)
        overlay.fill((*ACCENT_YELLOW_LIGHT, 60))
        screen.blit(overlay, rect.topleft)
        pygame.draw.rect(screen, ACCENT_YELLOW, rect, width=3)

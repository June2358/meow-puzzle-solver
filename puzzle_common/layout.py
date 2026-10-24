"""One board area and side panel policy for input and playback."""

from dataclasses import dataclass

import pygame

from .runtime import browser_viewport

BOARD_AREA = 540
MARGIN = 45
GRID_START_Y = 70
PANEL_GAP = 30
PANEL_WIDTH = 350
WINDOW_HEIGHT = 700
TOUCH_SIZE = 44
TOUCH_GAP = 8


@dataclass(frozen=True, slots=True)
class BoardLayout:
    cell_size: int
    board_rect: pygame.Rect
    panel_rect: pygame.Rect
    window_size: tuple[int, int]

    @property
    def stacked(self) -> bool:
        return self.panel_rect.top > self.board_rect.bottom

    @property
    def number_font_size(self) -> int:
        return min(36, max(12, round(self.cell_size * 0.65)))

    def cell_rect(self, cell: tuple[int, int]) -> pygame.Rect:
        row, column = cell
        return pygame.Rect(
            self.board_rect.left + column * self.cell_size,
            self.board_rect.top + row * self.cell_size,
            self.cell_size,
            self.cell_size,
        )

    def cell_at(self, position: tuple[int, int]) -> tuple[int, int] | None:
        if not self.board_rect.collidepoint(position):
            return None
        x, y = position
        return (
            (y - self.board_rect.top) // self.cell_size,
            (x - self.board_rect.left) // self.cell_size,
        )


def get_board_layout(
    size: int,
    viewport: tuple[int, int] | None = None,
    *,
    panel_height: int = WINDOW_HEIGHT - 2 * GRID_START_Y,
) -> BoardLayout:
    if type(size) is not int:
        raise TypeError("격자 크기는 정수여야 합니다.")
    if not 1 <= size <= BOARD_AREA:
        raise ValueError("격자 크기는 보드 영역 안에 들어가는 양수여야 합니다.")
    viewport = viewport if viewport is not None else browser_viewport()
    if viewport is not None and viewport[0] < 1010:
        width = max(360, viewport[0])
        area = min(BOARD_AREA, width - 64)
        cell_size = max(1, area // size)
        board_rect = pygame.Rect(0, 0, cell_size * size, cell_size * size)
        board_rect.midtop = (width // 2, GRID_START_Y)
        panel_rect = pygame.Rect(12, board_rect.bottom + 28, width - 24, panel_height)
        return BoardLayout(
            cell_size, board_rect, panel_rect, (width, panel_rect.bottom + 20)
        )
    cell_size = BOARD_AREA // size
    board_rect = pygame.Rect(0, 0, cell_size * size, cell_size * size)
    board_rect.center = (MARGIN + BOARD_AREA // 2, GRID_START_Y + BOARD_AREA // 2)
    panel_x = MARGIN + BOARD_AREA + PANEL_GAP
    return BoardLayout(
        cell_size,
        board_rect,
        pygame.Rect(
            panel_x, GRID_START_Y, PANEL_WIDTH, WINDOW_HEIGHT - 2 * GRID_START_Y
        ),
        (panel_x + PANEL_WIDTH + MARGIN, WINDOW_HEIGHT),
    )

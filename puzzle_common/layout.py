"""One board area and side panel policy for input and playback."""

from dataclasses import dataclass

import pygame

BOARD_AREA = 540
MARGIN = 45
GRID_START_Y = 70
PANEL_GAP = 30
PANEL_WIDTH = 350
WINDOW_HEIGHT = 700


@dataclass(frozen=True, slots=True)
class BoardLayout:
    cell_size: int
    board_rect: pygame.Rect
    panel_rect: pygame.Rect
    window_size: tuple[int, int]

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


def get_board_layout(size: int) -> BoardLayout:
    if type(size) is not int:
        raise TypeError("격자 크기는 정수여야 합니다.")
    if not 1 <= size <= BOARD_AREA:
        raise ValueError("격자 크기는 보드 영역 안에 들어가는 양수여야 합니다.")
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

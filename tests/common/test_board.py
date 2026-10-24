from dataclasses import replace

import pygame
import pytest

from puzzle_common.board import draw_board
from puzzle_common.layout import get_board_layout
from puzzle_common.ui_style import GRID_LINE, GRID_REGION_LINE, RED, get_fonts
from puzzle_common.view import BoardView, CellMark, CellView


def test_renderer_compares_regions_and_keeps_candidate_strike():
    layout = get_board_layout(2)
    surface = pygame.Surface(layout.window_size)
    cells = (
        (
            CellView(marks=(CellMark(text="1", slot=0, color=RED, struck=True),)),
            CellView(),
        ),
        (
            CellView(marks=(CellMark(kind="cat"),)),
            CellView(marks=(CellMark(kind="cross"),)),
        ),
    )
    draw_board(surface, layout, BoardView(None, cells, ((0, 0), (0, 1))), get_fonts())
    x, y = layout.board_rect.topleft
    step = layout.cell_size
    assert surface.get_at((x + step, y + step // 2))[:3] == GRID_LINE
    assert surface.get_at((x + step, y + step + step // 2))[:3] == GRID_REGION_LINE
    assert surface.get_at((x + step // 6, y + step // 6))[:3] == RED


@pytest.mark.parametrize("size", (1, 9, 26))
def test_renderer_draws_selected_cell_and_long_labels_at_all_sizes(size):
    layout = get_board_layout(size)
    cell = CellView(marks=(CellMark(text="긴 영역 이름" * 12),))
    cells = tuple((cell,) * size for _ in range(size))
    surface = pygame.Surface(layout.window_size)
    draw_board(
        surface,
        layout,
        BoardView(None, cells, tuple((0,) * size for _ in range(size))),
        get_fonts(),
        (0, 0),
    )


def test_renderer_rejects_mismatched_layout():
    cell = CellView()
    with pytest.raises(ValueError):
        draw_board(
            pygame.Surface((600, 600)),
            get_board_layout(9),
            BoardView(None, ((cell,),), ((0,),)),
            get_fonts(),
        )


def test_renderer_fits_long_labels_before_allocating_a_text_surface():
    font = get_fonts().number

    class BoundedFont:
        size = font.size
        get_height = font.get_height

        @staticmethod
        def render(text, antialias, color):
            assert len(text) < 100
            return font.render(text, antialias, color)

    layout = get_board_layout(1)
    view = BoardView(None, ((CellView(marks=(CellMark(text="A" * 10000),)),),), ((0,),))
    draw_board(
        pygame.Surface(layout.window_size),
        layout,
        view,
        replace(get_fonts(), number=BoundedFont()),
    )


def test_two_digit_region_label_remains_visible_on_a_26_cell_board():
    size = 26
    layout = get_board_layout(size)
    cell = CellView(marks=(CellMark(text="10"),))
    view = BoardView(
        None,
        tuple((cell,) * size for _ in range(size)),
        tuple((0,) * size for _ in range(size)),
    )
    surface = pygame.Surface(layout.window_size)

    draw_board(surface, layout, view, get_fonts())

    interior = layout.cell_rect((10, 10)).inflate(-4, -4)
    assert any(
        surface.get_at((x, y))[:3] != cell.background
        for x in range(interior.left, interior.right)
        for y in range(interior.top, interior.bottom)
    )

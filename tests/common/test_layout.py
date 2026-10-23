import pygame
import pytest

from meow.ui_style import get_fonts as region_fonts
from puzzle_common.layout import get_board_layout
from sudoku.ui_style import get_fonts as digit_fonts


@pytest.mark.parametrize("size", (1, 4, 8, 9, 26))
def test_board_sizes_share_one_screen_and_panel(size):
    layout = get_board_layout(size)
    assert layout.window_size == (1010, 700)
    assert layout.panel_rect == pygame.Rect(615, 70, 350, 560)
    assert layout.cell_size == 540 // size
    assert layout.board_rect.size == (layout.cell_size * size,) * 2
    assert layout.board_rect.center == (315, 340)


@pytest.mark.parametrize("size", (0, -1, 541))
def test_invalid_layout_size_is_rejected(size):
    with pytest.raises(ValueError):
        get_board_layout(size)


@pytest.mark.parametrize("size", (True, 9.0, "9"))
def test_layout_size_must_be_an_integer(size):
    with pytest.raises(TypeError):
        get_board_layout(size)


def test_info_font_is_shared_while_domain_fonts_keep_their_sizes():
    regions, digits = region_fonts(), digit_fonts()
    assert regions.info.get_point_size() == digits.info.get_point_size() == 15
    assert regions.info.style_name == digits.info.style_name == "Regular"
    assert (regions.number.get_point_size(), regions.candidate.get_point_size()) == (
        34,
        13,
    )
    assert (digits.number.get_point_size(), digits.candidate.get_point_size()) == (
        38,
        15,
    )

import pygame
import pytest


def test_shared_grid_uses_the_requested_origin_size_and_spacing():
    from puzzle_common.ui_style import draw_grid_lines

    surface = pygame.Surface((80, 80))
    surface.fill("white")
    draw_grid_lines(surface, (10, 15), 20, 2, color=(0, 0, 0), width=1)

    for point in ((10, 20), (30, 20), (50, 20), (20, 15), (20, 35), (20, 55)):
        assert surface.get_at(point)[:3] == (0, 0, 0)
    assert surface.get_at((20, 20))[:3] == (255, 255, 255)
    assert surface.get_at((51, 56))[:3] == (255, 255, 255)


@pytest.mark.parametrize("cell, expected", [((0, 0), "R1C1"), ((25, 8), "R26C9")])
def test_shared_cell_labels_use_one_based_coordinates(cell, expected):
    from puzzle_common.coordinates import cell_name

    assert cell_name(cell) == expected

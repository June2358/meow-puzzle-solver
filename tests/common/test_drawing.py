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


@pytest.mark.parametrize(
    "hover_color, expected",
    ((None, (62, 72, 82)), ((99, 80, 70), (99, 80, 70))),
)
def test_button_draw_uses_the_current_pointer_without_a_separate_hover_update(
    monkeypatch, hover_color, expected
):
    from puzzle_common.ui_components import Button

    pygame.font.init()
    screen = pygame.Surface((100, 80))
    button = Button(
        pygame.Rect(10, 10, 60, 40),
        "",
        (50, 60, 70),
        pygame.font.Font(None, 20),
        hover_color=hover_color,
        border_color=(1, 2, 3),
    )
    for pointer, color in (
        ((0, 0), (50, 60, 70)),
        ((20, 20), expected),
        ((0, 0), (50, 60, 70)),
    ):
        monkeypatch.setattr(pygame.mouse, "get_pos", lambda pointer=pointer: pointer)
        button.draw(screen)

        assert screen.get_at((30, 20))[:3] == color
        assert screen.get_at((10, 25))[:3] == (1, 2, 3)

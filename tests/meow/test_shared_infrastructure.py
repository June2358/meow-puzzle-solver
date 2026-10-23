import pytest

import meow.input_dialog as meow_input
import meow.visualizer as meow_visualizer
import sudoku.input_dialog as sudoku_input
import sudoku.visualizer as sudoku_visualizer
from puzzle_common.ui_style import Fonts


@pytest.mark.parametrize(
    "name",
    (
        "Button",
        "next_frame",
        "configure_display",
        "wrap_text",
        "ClipboardError",
        "copy_text",
        "paste_text",
        "WebTextDialog",
        "WebTextDialogError",
        "is_web_runtime",
    ),
)
def test_input_screens_use_the_same_shared_implementation(name: str) -> None:
    implementation = getattr(meow_input, name)

    assert implementation is getattr(sudoku_input, name)
    assert implementation.__module__.startswith("puzzle_common.")


@pytest.mark.parametrize("name", ("Button", "next_frame", "configure_display"))
def test_playback_screens_share_the_input_screens_implementation(name: str) -> None:
    implementation = getattr(meow_input, name)

    assert implementation is getattr(meow_visualizer, name)
    assert implementation is getattr(sudoku_visualizer, name)


def test_shared_fonts_keep_the_two_apps_number_and_candidate_sizes() -> None:
    meow_fonts = meow_input.get_fonts()
    sudoku_fonts = sudoku_input.get_fonts()

    assert type(meow_fonts) is type(sudoku_fonts) is Fonts
    assert meow_fonts.number.get_point_size() == 34
    assert meow_fonts.candidate.get_point_size() == 13
    assert sudoku_fonts.number.get_point_size() == 38
    assert sudoku_fonts.candidate.get_point_size() == 15

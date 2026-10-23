"""Shared input behavior must hold for both real puzzle editors."""

import asyncio
from dataclasses import replace

import pygame
import pytest

from meow.input_dialog import MeowInputDialog
from sudoku.input_dialog import SudokuInputDialog


class PendingDialog:
    def __init__(self):
        self.closed = False

    def poll(self):
        return None

    def close(self):
        self.closed = True


@pytest.fixture(params=[MeowInputDialog, SudokuInputDialog])
def dialog(request):
    pygame.init()
    instance = request.param()
    yield instance
    pygame.quit()


def test_active_modal_blocks_background_edits_and_still_allows_quit(dialog):
    dialog.selected_cell = (0, 0)
    before = str(getattr(dialog, "draft", getattr(dialog, "board", None)))
    dialog._open_web_dialog(PendingDialog)

    dialog._handle_events(
        [
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="A", mod=0),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3, unicode="3", mod=0),
            pygame.event.Event(pygame.QUIT),
        ]
    )

    assert str(getattr(dialog, "draft", getattr(dialog, "board", None))) == before
    assert not dialog.running


def test_open_modal_is_cleaned_up_when_initial_drawing_fails(dialog, monkeypatch):
    browser_dialog = PendingDialog()
    dialog._open_web_dialog(lambda: browser_dialog)

    def fail_to_draw():
        raise RuntimeError("drawing failed")

    monkeypatch.setattr(dialog, "draw", fail_to_draw)
    with pytest.raises(RuntimeError, match="drawing failed"):
        asyncio.run(dialog.run())

    assert browser_dialog.closed
    assert dialog._web_text_dialog is None


def test_arrow_navigation_clamps_to_the_board_and_moves_one_cell(dialog):
    dialog.selected_cell = (0, 0)
    for key in (pygame.K_LEFT, pygame.K_UP):
        dialog._handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))
    assert dialog.selected_cell == (0, 0)

    for key in (pygame.K_RIGHT, pygame.K_DOWN):
        dialog._handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))
    assert dialog.selected_cell == (1, 1)

    edge = dialog.grid_width // dialog.cell_size - 1
    dialog.selected_cell = (edge, edge)
    for key in (pygame.K_RIGHT, pygame.K_DOWN):
        dialog._handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=key, mod=0))
    assert dialog.selected_cell == (edge, edge)


def test_opening_a_modal_blocks_later_events_in_the_same_batch(dialog, monkeypatch):
    import puzzle_common.input_dialog as common_input

    monkeypatch.setattr(common_input, "is_web_runtime", lambda: True)
    monkeypatch.setattr(common_input, "WebTextDialog", lambda **kwargs: PendingDialog())
    dialog.selected_cell = (0, 0)
    before = str(getattr(dialog, "draft", getattr(dialog, "board", None)))

    dialog._handle_events(
        [
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=dialog.paste_button.rect.center
            ),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_a, unicode="A", mod=0),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_3, unicode="3", mod=0),
        ]
    )

    assert str(getattr(dialog, "draft", getattr(dialog, "board", None))) == before
    assert dialog._web_text_dialog is not None
    dialog._close_web_text_dialog()


@pytest.mark.parametrize(
    ("key", "mod"),
    [
        (pygame.K_UP, 0),
        (pygame.K_DOWN, 0),
        (pygame.K_LEFT, 0),
        (pygame.K_RIGHT, 0),
        (pygame.K_TAB, 0),
        (pygame.K_TAB, pygame.KMOD_SHIFT),
    ],
)
def test_navigation_without_selection_selects_the_first_cell(dialog, key, mod):
    dialog._handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod))

    assert dialog.selected_cell == (0, 0)


def test_tab_moves_in_cell_order_and_stops_at_both_ends(dialog):
    size = dialog.grid_width // dialog.cell_size
    dialog.selected_cell = (0, size - 1)
    dialog._handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=0))
    assert dialog.selected_cell == (1, 0)
    dialog._handle_keydown(
        pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=pygame.KMOD_SHIFT)
    )
    assert dialog.selected_cell == (0, size - 1)

    for cell, mod in [((0, 0), pygame.KMOD_SHIFT), ((size - 1, size - 1), 0)]:
        dialog.selected_cell = cell
        dialog._handle_keydown(
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_TAB, mod=mod)
        )
        assert dialog.selected_cell == cell


@pytest.mark.parametrize("mod", [pygame.KMOD_CTRL, pygame.KMOD_ALT, pygame.KMOD_GUI])
@pytest.mark.parametrize(
    ("key", "text"),
    [
        (pygame.K_a, "A"),
        (pygame.K_3, "3"),
        (pygame.K_DELETE, ""),
        (pygame.K_BACKSPACE, ""),
        (pygame.K_c, "C"),
        (pygame.K_r, "R"),
        (pygame.K_s, "S"),
        (pygame.K_RETURN, "\r"),
        (pygame.K_KP_ENTER, "\r"),
        (pygame.K_TAB, "\t"),
        (pygame.K_RIGHT, ""),
    ],
)
def test_command_modifiers_do_not_edit_navigate_or_start(dialog, mod, key, text):
    dialog._load_preset(0)
    dialog.selected_cell = (0, 0)
    before = str(getattr(dialog, "draft", getattr(dialog, "board", None)))
    message = (dialog.validation_error, dialog.notice_message)

    result = dialog._handle_keydown(
        pygame.event.Event(pygame.KEYDOWN, key=key, unicode=text, mod=mod)
    )

    assert str(getattr(dialog, "draft", getattr(dialog, "board", None))) == before
    assert (dialog.validation_error, dialog.notice_message) == message
    assert dialog.selected_cell == (0, 0)
    assert result is None
    assert dialog.running


@pytest.mark.parametrize("message_method", ["_show_error", "_show_notice"])
def test_reentering_the_same_value_keeps_feedback(dialog, message_method):
    if isinstance(dialog, MeowInputDialog):
        dialog._set_cell((0, 0), "A", advance=False)
        key, text = pygame.K_a, "A"
    else:
        dialog._set_cell(0, 0, 3)
        key, text = pygame.K_3, "3"
    dialog.selected_cell = (0, 0)
    getattr(dialog, message_method)("원본 입력을 확인하세요.")
    before = (dialog.validation_error, dialog.notice_message)

    dialog._handle_keydown(
        pygame.event.Event(pygame.KEYDOWN, key=key, unicode=text, mod=0)
    )

    assert (dialog.validation_error, dialog.notice_message) == before
    assert dialog.selected_cell == (0, 0)


def test_input_uses_shared_layout_for_board_panel_and_window(dialog):
    assert dialog.screen.get_size() == (1010, 700)
    assert (dialog.panel_x, dialog.panel_width) == (615, 350)
    if isinstance(dialog, MeowInputDialog):
        assert (dialog.cell_size, dialog.grid_width) == (67, 536)
        assert (dialog.grid_start_x, dialog.grid_start_y) == (47, 72)
    else:
        assert (dialog.cell_size, dialog.grid_width) == (60, 540)
        assert (dialog.grid_start_x, dialog.grid_start_y) == (45, 70)


def test_panel_information_uses_info_font_instead_of_board_candidates(dialog):
    assert hasattr(dialog.fonts, "info")
    rendered = []

    class RecordingFont:
        def __init__(self, font):
            self.font = font

        def __getattr__(self, name):
            return getattr(self.font, name)

        def render(self, text, *args):
            rendered.append(text)
            return self.font.render(text, *args)

    class BoardOnlyFont:
        def render(self, *args):
            pytest.fail("Panel text must not use the board candidate font")

        def size(self, *args):
            pytest.fail("Panel wrapping must not use the board candidate font")

    dialog.fonts = replace(
        dialog.fonts, info=RecordingFont(dialog.fonts.info), candidate=BoardOnlyFont()
    )
    dialog._show_error("입력을 확인하세요.")

    dialog._draw_panel()

    assert "입력을 확인하세요." in rendered
    assert any("Tab" in text for text in rendered)
    if dialog.progress_text:
        assert dialog.progress_text in rendered

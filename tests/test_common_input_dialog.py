"""Shared input behavior must hold for both real puzzle editors."""

import asyncio

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

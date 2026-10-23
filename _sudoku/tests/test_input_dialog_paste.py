import asyncio
import json

import pygame
import pytest
from sample_puzzles import UNIQUE_GRID

import sudoku.input_dialog as input_dialog_module
from sudoku.board import Puzzle, validate_grid
from sudoku.input_dialog import SudokuInputDialog
from sudoku.web_text_dialog import (
    WebTextDialogError,
    WebTextDialogResult,
)


class FakeWebDialog:
    def __init__(self, *results: WebTextDialogResult | None) -> None:
        self.results = list(results)
        self.errors: list[str] = []
        self.closed = False

    def poll(self) -> WebTextDialogResult | None:
        return self.results.pop(0) if self.results else None

    def show_error(self, message: str) -> None:
        self.errors.append(message)

    def close(self) -> None:
        self.closed = True


@pytest.fixture
def dialog() -> SudokuInputDialog:
    pygame.init()
    instance = SudokuInputDialog()
    yield instance
    pygame.quit()


def test_ctrl_v_then_start_returns_the_pasted_puzzle(
    dialog: SudokuInputDialog, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        input_dialog_module, "paste_text", lambda: json.dumps(UNIQUE_GRID)
    )
    event = pygame.event.Event(
        pygame.KEYDOWN,
        key=pygame.K_v,
        mod=pygame.KMOD_CTRL,
    )

    assert dialog._handle_keydown(event) is None
    result = dialog._handle_start()

    assert isinstance(result, Puzzle)
    assert result.grid == tuple(tuple(row) for row in UNIQUE_GRID)


def test_invalid_paste_preserves_the_existing_board(
    dialog: SudokuInputDialog, monkeypatch: pytest.MonkeyPatch
) -> None:
    dialog._replace_board(UNIQUE_GRID)
    before = validate_grid(dialog.board)
    monkeypatch.setattr(input_dialog_module, "paste_text", lambda: "not JSON")

    dialog._paste_matrix()

    assert validate_grid(dialog.board) == before
    assert dialog.validation_error


def test_conflicting_matrix_can_be_edited_but_not_started(
    dialog: SudokuInputDialog, monkeypatch: pytest.MonkeyPatch
) -> None:
    conflicting = [row[:] for row in UNIQUE_GRID]
    conflicting[0][1] = 5
    monkeypatch.setattr(
        input_dialog_module, "paste_text", lambda: json.dumps(conflicting)
    )

    dialog._paste_matrix()

    assert validate_grid(dialog.board)[0][:2] == (5, 5)
    assert dialog._handle_start() is None
    assert dialog.validation_error


def test_web_json_submit_reuses_parser_then_closes_on_success(
    dialog: SudokuInputDialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser_dialog = FakeWebDialog(
        WebTextDialogResult(submitted=True, text=json.dumps(UNIQUE_GRID, indent=2))
    )
    monkeypatch.setattr(input_dialog_module, "is_web_runtime", lambda: True)
    monkeypatch.setattr(
        input_dialog_module,
        "open_json_dialog",
        lambda: browser_dialog,
    )

    dialog._handle_json_action()

    assert dialog._web_text_dialog is browser_dialog
    assert dialog._poll_web_text_dialog()
    assert validate_grid(dialog.board) == tuple(tuple(row) for row in UNIQUE_GRID)
    assert browser_dialog.closed
    assert dialog._web_text_dialog is None


def test_invalid_web_json_preserves_text_dialog_and_board(
    dialog: SudokuInputDialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialog._replace_board(UNIQUE_GRID)
    before = validate_grid(dialog.board)
    browser_dialog = FakeWebDialog(WebTextDialogResult(submitted=True, text="not JSON"))
    monkeypatch.setattr(input_dialog_module, "is_web_runtime", lambda: True)
    monkeypatch.setattr(
        input_dialog_module,
        "open_json_dialog",
        lambda: browser_dialog,
    )

    dialog._handle_json_action()

    assert not dialog._poll_web_text_dialog()
    assert validate_grid(dialog.board) == before
    assert browser_dialog.errors
    assert not browser_dialog.closed
    assert dialog._web_text_dialog is browser_dialog


def test_web_prompt_is_shown_without_clipboard_access(
    dialog: SudokuInputDialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser_dialog = FakeWebDialog()
    prompt_calls: list[str] = []
    monkeypatch.setattr(input_dialog_module, "is_web_runtime", lambda: True)
    monkeypatch.setattr(
        input_dialog_module,
        "open_prompt_dialog",
        lambda text: prompt_calls.append(text) or browser_dialog,
    )
    monkeypatch.setattr(
        input_dialog_module,
        "copy_text",
        lambda text: pytest.fail("Web prompt must not use clipboard write"),
    )

    dialog._handle_prompt_action()

    assert prompt_calls == [input_dialog_module.OCR_MATRIX_PROMPT]
    assert dialog._web_text_dialog is browser_dialog


def test_web_dialog_bridge_failure_becomes_pygame_validation_error(
    dialog: SudokuInputDialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_to_open():
        raise WebTextDialogError("DOM bridge failed")

    monkeypatch.setattr(input_dialog_module, "is_web_runtime", lambda: True)
    monkeypatch.setattr(input_dialog_module, "open_json_dialog", fail_to_open)

    dialog._handle_json_action()

    assert dialog._web_text_dialog is None
    assert dialog.validation_error == "DOM bridge failed"


def test_run_yields_a_frame_then_handles_a_quit_event(
    dialog: SudokuInputDialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    draw_calls: list[None] = []
    frame_calls: list[pygame.time.Clock] = []

    monkeypatch.setattr(dialog, "draw", lambda: draw_calls.append(None))

    async def advance_frame(clock: pygame.time.Clock) -> float:
        frame_calls.append(clock)
        await asyncio.sleep(0)
        return 1 / 60

    monkeypatch.setattr(input_dialog_module, "next_frame", advance_frame)
    monkeypatch.setattr(
        pygame.event,
        "get",
        lambda: [pygame.event.Event(pygame.QUIT)],
    )

    assert asyncio.run(dialog.run()) is None
    assert draw_calls == [None]
    assert len(frame_calls) == 1


def test_run_cleans_up_an_open_web_dialog_on_quit(
    dialog: SudokuInputDialog,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    browser_dialog = FakeWebDialog(None)
    dialog._web_text_dialog = browser_dialog

    async def advance_frame(clock: pygame.time.Clock) -> float:
        await asyncio.sleep(0)
        return 1 / 60

    monkeypatch.setattr(dialog, "draw", lambda: None)
    monkeypatch.setattr(input_dialog_module, "next_frame", advance_frame)
    monkeypatch.setattr(
        pygame.event,
        "get",
        lambda: [pygame.event.Event(pygame.QUIT)],
    )

    assert asyncio.run(dialog.run()) is None
    assert browser_dialog.closed
    assert dialog._web_text_dialog is None

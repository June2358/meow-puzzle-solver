from __future__ import annotations

import asyncio
import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

import puzzle_common.input_dialog as input_dialog_module
from meow.input_dialog import MeowInputDialog
from meow.puzzle_catalog import load_preset
from puzzle_common.web_text_dialog import WebTextDialogResult


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


@pytest.fixture(scope="module", autouse=True)
def pygame_runtime():
    pygame.init()
    yield
    pygame.quit()


def test_preset_then_start_returns_the_selected_puzzle() -> None:
    dialog = MeowInputDialog()

    dialog._load_preset(2)
    puzzle = dialog._handle_start()

    assert puzzle is not None
    assert puzzle.region_grid == load_preset("어려움").region_grid


def test_direct_input_reports_an_empty_cell_then_starts_when_complete() -> None:
    dialog = MeowInputDialog(initial_grid=(("A", "A"), (None, "B")))

    assert dialog._handle_start() is None
    assert dialog.validation_error and "R2C1" in dialog.validation_error
    assert dialog.selected_cell == (1, 0)

    dialog._set_cell((1, 0), "B", advance=False)
    puzzle = dialog._handle_start()

    assert puzzle is not None
    assert puzzle.region_grid == (("A", "A"), ("B", "B"))


def test_size_field_creates_a_new_empty_grid() -> None:
    dialog = MeowInputDialog(initial_grid=(("A", "A"), ("B", "B")))
    dialog.size_text = "4"

    dialog._apply_size()

    assert dialog.draft.size == 4
    assert dialog.draft.filled_count == 0


def test_json_paste_is_atomic(monkeypatch: pytest.MonkeyPatch) -> None:
    dialog = MeowInputDialog(initial_grid=(("A", "A"), ("B", "B")))
    document = {
        "regions": [
            ["dark red", "dark red", "dark red"],
            ["밝은 파랑", "밝은 파랑", "밝은 파랑"],
            ["green", "green", "green"],
        ]
    }
    monkeypatch.setattr(
        input_dialog_module,
        "paste_text",
        lambda: json.dumps(document, ensure_ascii=False),
    )

    dialog._handle_mouse_click(dialog.paste_button.rect.center)

    assert dialog.draft.grid[0][0] == "dark red"
    assert dialog.draft.grid[1][1] == "밝은 파랑"

    before = dialog.draft
    document["name"] = "지원하지 않는 필드"
    monkeypatch.setattr(
        input_dialog_module,
        "paste_text",
        lambda: json.dumps(document, ensure_ascii=False),
    )
    dialog._handle_keydown(
        pygame.event.Event(
            pygame.KEYDOWN,
            key=pygame.K_v,
            mod=pygame.KMOD_CTRL,
        )
    )

    assert dialog.draft is before
    assert dialog.validation_error and "지원하지 않는 JSON 필드" in (
        dialog.validation_error
    )


def test_web_json_submit_reuses_parser_then_closes_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialog = MeowInputDialog()
    document = {
        "regions": [
            ["A", "A", "B"],
            ["C", "B", "B"],
            ["C", "C", "B"],
        ]
    }
    browser_dialog = FakeWebDialog(
        WebTextDialogResult(submitted=True, text=json.dumps(document))
    )
    monkeypatch.setattr(input_dialog_module, "is_web_runtime", lambda: True)
    monkeypatch.setattr(
        input_dialog_module,
        "WebTextDialog",
        lambda **kwargs: browser_dialog,
    )

    dialog._handle_json_action()

    assert dialog._web_text_dialog is browser_dialog
    assert dialog._poll_web_text_dialog()
    assert dialog.draft.grid == (
        ("A", "A", "B"),
        ("C", "B", "B"),
        ("C", "C", "B"),
    )
    assert browser_dialog.closed
    assert dialog._web_text_dialog is None


def test_invalid_web_json_preserves_text_dialog_and_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialog = MeowInputDialog(initial_grid=(("A", "A"), ("B", "B")))
    before = dialog.draft
    browser_dialog = FakeWebDialog(WebTextDialogResult(submitted=True, text="not JSON"))
    monkeypatch.setattr(input_dialog_module, "is_web_runtime", lambda: True)
    monkeypatch.setattr(
        input_dialog_module,
        "WebTextDialog",
        lambda **kwargs: browser_dialog,
    )

    dialog._handle_json_action()

    assert not dialog._poll_web_text_dialog()
    assert dialog.draft is before
    assert browser_dialog.errors
    assert not browser_dialog.closed
    assert dialog._web_text_dialog is browser_dialog


def test_run_yields_a_frame_then_handles_a_quit_event(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialog = MeowInputDialog()
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


def test_region_drag_stops_when_the_button_is_released() -> None:
    dialog = MeowInputDialog(initial_grid=(("A", "A"), ("B", "B")))
    x = dialog.grid_start_x + dialog.cell_size // 2
    y = dialog.grid_start_y + dialog.cell_size // 2
    dialog._handle_events(
        [
            pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(x, y)),
            pygame.event.Event(
                pygame.MOUSEMOTION, pos=(x, y + dialog.cell_size), buttons=(1, 0, 0)
            ),
            pygame.event.Event(
                pygame.MOUSEBUTTONUP, button=1, pos=(x, y + dialog.cell_size)
            ),
            pygame.event.Event(
                pygame.MOUSEMOTION,
                pos=(x + dialog.cell_size, y + dialog.cell_size),
                buttons=(1, 0, 0),
            ),
        ]
    )

    assert dialog.draft.grid == (("A", "A"), ("A", "B"))


def test_size_field_enter_creates_the_grid_without_starting_the_solver() -> None:
    dialog = MeowInputDialog(initial_grid=(("A", "A"), ("B", "B")))
    dialog._handle_events(
        [
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=dialog.size_field_rect.center
            ),
            pygame.event.Event(pygame.KEYDOWN, key=pygame.K_4, unicode="4", mod=0),
            pygame.event.Event(
                pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r", mod=0
            ),
        ]
    )

    assert dialog.draft.size == 4
    assert dialog.draft.filled_count == 0
    assert dialog.running

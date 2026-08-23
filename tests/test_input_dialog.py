from __future__ import annotations

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

import meow.input_dialog as input_dialog_module
from meow.input_dialog import MeowInputDialog
from meow.matrix_input import VISION_REGION_PROMPT
from meow.puzzle_catalog import load_preset


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
    assert len(dialog.preset_buttons) == 6
    assert len({button.rect.x for button in dialog.preset_buttons}) == 3
    assert len({button.rect.y for button in dialog.preset_buttons}) == 2
    assert max(button.rect.bottom for button in dialog.preset_buttons) < (
        dialog.size_field_rect.top
    )
    assert dialog.copy_prompt_button.rect.right < dialog.paste_button.rect.left
    for button in (dialog.copy_prompt_button, dialog.paste_button):
        assert button.font.size(button.text)[0] < button.rect.width
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


def test_copy_prompt_uses_the_region_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dialog = MeowInputDialog()
    copied: list[str] = []
    monkeypatch.setattr(input_dialog_module, "copy_text", copied.append)

    dialog._handle_mouse_click(dialog.copy_prompt_button.rect.center)

    assert copied == [VISION_REGION_PROMPT]
    assert dialog.notice_message

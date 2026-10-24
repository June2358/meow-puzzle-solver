"""One editor keeps both puzzle definitions safe under the same controls."""

import asyncio
import json
from dataclasses import replace

import pygame
import pytest

from puzzle_common.input_dialog import InputDialog


class PendingDialog:
    def __init__(self):
        self.closed = False

    def poll(self):
        return None

    def close(self):
        self.closed = True


@pytest.fixture(params=["meow", "sudoku"])
def definition(request):
    if request.param == "meow":
        from meow.definition import DEFINITION
    else:
        from sudoku.definition import DEFINITION
    return DEFINITION


@pytest.fixture
def dialog(definition):
    pygame.init()
    instance = InputDialog(definition)
    yield instance
    instance._close_web_text_dialog()
    pygame.quit()


def key(key_code, text="", mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=key_code, unicode=text, mod=mod)


def test_editing_replaces_immutable_draft_and_delete_uses_definition_empty(dialog):
    original = dialog.draft
    dialog.selected_cell = (0, 0)
    value = dialog.definition.symbols[0]
    dialog._handle_events([key(pygame.key.key_code(str(value).lower()), str(value))])
    assert dialog.draft[0][0] == value
    assert original[0][0] == dialog.definition.empty
    assert isinstance(dialog.draft, tuple)
    assert all(isinstance(row, tuple) for row in dialog.draft)
    dialog._handle_events([key(pygame.K_DELETE)])
    assert dialog.draft == original


@pytest.mark.parametrize(
    "delete_key", [pygame.K_0, pygame.K_KP0, pygame.K_DELETE, pygame.K_BACKSPACE]
)
def test_all_clear_keys_clear_selected_cell(dialog, delete_key):
    dialog._load_preset(0)
    dialog.selected_cell = (0, 0)
    dialog._handle_events([key(delete_key)])
    assert dialog.draft[0][0] == dialog.definition.empty


@pytest.mark.parametrize("number", range(1, 10))
def test_keypad_numbers_are_mapped_individually(dialog, number):
    dialog.selected_cell = (0, 0)
    dialog._handle_events([key(getattr(pygame, f"K_KP{number}"))])
    expected = next(
        (value for value in dialog.definition.symbols if str(value) == str(number)),
        dialog.definition.empty,
    )
    assert dialog.draft[0][0] == expected


def test_invalid_json_preserves_draft_selection_and_layout(dialog):
    dialog._load_preset(0)
    dialog.selected_cell = (1, 1)
    before = dialog.draft, dialog.selected_cell, dialog.layout
    for text in ("{", "null", "[[true]]", '{"regions":[["A"],[]]}'):
        with pytest.raises(ValueError):
            dialog._load_json_text(text)
        assert (dialog.draft, dialog.selected_cell, dialog.layout) == before


def test_preset_and_json_create_native_puzzle(dialog):
    dialog._load_preset(0)
    grid = dialog.draft
    document = {"regions": grid} if dialog.definition.key == "meow" else grid
    dialog._load_json_text(json.dumps(document))
    puzzle = dialog._handle_start()
    assert puzzle is not None
    assert dialog.definition.grid(puzzle) == grid
    assert not dialog.running
    assert not dialog.quit_requested


def test_blank_draft_cannot_start(dialog):
    assert dialog._handle_start() is None
    assert dialog.validation_error
    assert dialog.running


def test_invalid_initial_grid_is_rejected_before_display(definition, monkeypatch):
    import puzzle_common.input_dialog as common_input

    def unexpected_display(*args):
        pytest.fail("Invalid drafts must be rejected before opening the editor")

    monkeypatch.setattr(common_input, "configure_display", unexpected_display)
    with pytest.raises(ValueError):
        InputDialog(definition, initial_grid=[[True]])


def test_unchanged_cell_keeps_feedback_and_selection(dialog):
    value = dialog.definition.symbols[0]
    dialog.selected_cell = (0, 0)
    event = key(pygame.key.key_code(str(value).lower()), str(value))
    dialog._handle_events([event])
    dialog._show_error("원본 입력을 확인하세요.")
    before = dialog.draft
    dialog._handle_events([event])
    assert dialog.draft is before
    assert dialog.validation_error == "원본 입력을 확인하세요."
    assert dialog.selected_cell == (0, 0)


def test_conflicting_sudoku_json_is_editable_and_highlighted():
    from sudoku.definition import DEFINITION

    pygame.init()
    try:
        dialog = InputDialog(DEFINITION)
        grid = [[0] * 9 for _ in range(9)]
        grid[0][:2] = [1, 1]
        dialog._load_json_text(json.dumps(grid))
        assert dialog.draft[0][:3] == (1, 1, 0)
        view = DEFINITION.editor_view(dialog.draft)
        assert view.cells[0][0] != view.cells[1][3]
        assert dialog._handle_start() is None
        assert dialog.validation_error
        dialog.selected_cell = (0, 1)
        dialog._handle_events([key(pygame.K_2, "2")])
        assert dialog.draft[0][:3] == (1, 2, 0)
    finally:
        pygame.quit()


def test_size_changes_are_bounded_and_reset_selection(dialog):
    low, high = dialog.definition.size_range
    before = dialog.draft
    for text in ("0", str(high + 1), "", "9" * 5000):
        dialog.size_text = text
        dialog._apply_size()
        assert dialog.draft is before
        assert dialog.validation_error
    dialog.selected_cell = (0, 0)
    dialog.size_text = str(low)
    dialog._apply_size()
    assert len(dialog.draft) == low
    assert all(
        value == dialog.definition.empty for row in dialog.draft for value in row
    )
    assert dialog.selected_cell is None
    assert dialog.board_size == low


def test_paint_drag_copies_filled_cell_and_stops_on_focus_loss(dialog):
    dialog._load_preset(0)
    source = next(
        (r, c)
        for r, row in enumerate(dialog.draft)
        for c, value in enumerate(row)
        if value != dialog.definition.empty
    )
    value = dialog.draft[source[0]][source[1]]
    target = (len(dialog.draft) - 1, len(dialog.draft) - 1)
    dialog._handle_events(
        [
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=dialog.layout.cell_rect(source).center,
            ),
            pygame.event.Event(
                pygame.MOUSEMOTION,
                pos=dialog.layout.cell_rect(target).center,
                buttons=(1, 0, 0),
            ),
            pygame.event.Event(pygame.WINDOWFOCUSLOST),
        ]
    )
    assert dialog.draft[target[0]][target[1]] == value
    before = dialog.draft
    dialog._handle_events(
        [
            pygame.event.Event(
                pygame.MOUSEMOTION,
                pos=dialog.layout.cell_rect((0, 0)).center,
                buttons=(1, 0, 0),
            )
        ]
    )
    assert dialog.draft is before


def test_active_modal_blocks_background_edits_and_still_allows_quit(dialog):
    dialog.selected_cell = (0, 0)
    before = dialog.draft
    dialog._open_web_dialog(PendingDialog)
    dialog._handle_events(
        [key(pygame.K_a, "A"), key(pygame.K_3, "3"), pygame.event.Event(pygame.QUIT)]
    )
    assert dialog.draft is before
    assert not dialog.running
    assert dialog.quit_requested


def test_opening_modal_ends_a_paint_gesture(dialog):
    value = dialog.definition.symbols[0]
    dialog._set_cell((0, 0), value)
    dialog._handle_events(
        [
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN,
                button=1,
                pos=dialog.layout.cell_rect((0, 0)).center,
            )
        ]
    )
    dialog._open_web_dialog(PendingDialog)
    dialog._close_web_text_dialog()
    before = dialog.draft
    dialog._handle_events(
        [
            pygame.event.Event(
                pygame.MOUSEMOTION,
                buttons=(1, 0, 0),
                pos=dialog.layout.cell_rect((1, 1)).center,
            )
        ]
    )
    assert dialog.draft is before


@pytest.mark.parametrize(
    "events",
    [
        [key(pygame.K_RETURN), pygame.event.Event(pygame.QUIT)],
        [key(pygame.K_a, "A"), pygame.event.Event(pygame.QUIT)],
        [key(pygame.K_ESCAPE), pygame.event.Event(pygame.QUIT)],
    ],
)
def test_quit_wins_over_every_queued_action(dialog, events):
    dialog._load_preset(0)
    before = dialog.draft
    assert dialog._handle_events(events) is None
    assert dialog.draft is before
    assert dialog.quit_requested
    assert not dialog.running


def test_escape_returns_to_selector_and_discards_later_events(dialog):
    dialog._load_preset(0)
    before = dialog.draft
    assert dialog._handle_events([key(pygame.K_ESCAPE), key(pygame.K_RETURN)]) is None
    assert not dialog.running
    assert not dialog.quit_requested
    assert dialog.draft is before


def test_quit_closes_modal_without_polling_it(dialog, monkeypatch):
    import puzzle_common.input_dialog as common_input

    class QuittingDialog(PendingDialog):
        def poll(self):
            pytest.fail("A closed input screen must not read browser input")

    browser_dialog = QuittingDialog()
    dialog._open_web_dialog(lambda: browser_dialog)

    async def next_frame(clock):
        return 0

    monkeypatch.setattr(common_input, "next_frame", next_frame)
    monkeypatch.setattr(pygame.event, "get", lambda: [pygame.event.Event(pygame.QUIT)])
    assert asyncio.run(dialog.run()) is None
    assert browser_dialog.closed


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


def test_arrows_clamp_and_tab_moves_in_cell_order(dialog):
    dialog._handle_events([key(pygame.K_UP), key(pygame.K_LEFT)])
    assert dialog.selected_cell == (0, 0)
    dialog._handle_events([key(pygame.K_RIGHT), key(pygame.K_DOWN)])
    assert dialog.selected_cell == (1, 1)
    size = len(dialog.draft)
    dialog.selected_cell = (0, size - 1)
    dialog._handle_events([key(pygame.K_TAB)])
    assert dialog.selected_cell == (1, 0)
    dialog._handle_events([key(pygame.K_TAB, mod=pygame.KMOD_SHIFT)])
    assert dialog.selected_cell == (0, size - 1)
    dialog.selected_cell = (size - 1, size - 1)
    dialog._handle_events([key(pygame.K_DOWN), key(pygame.K_RIGHT), key(pygame.K_TAB)])
    assert dialog.selected_cell == (size - 1, size - 1)


def test_opening_a_modal_blocks_later_events_in_the_same_batch(dialog, monkeypatch):
    import puzzle_common.input_dialog as common_input

    monkeypatch.setattr(common_input, "is_web_runtime", lambda: True)
    monkeypatch.setattr(common_input, "WebTextDialog", lambda **kwargs: PendingDialog())
    dialog.selected_cell = (0, 0)
    before = dialog.draft
    dialog._handle_events(
        [
            pygame.event.Event(
                pygame.MOUSEBUTTONDOWN, button=1, pos=dialog.paste_button.rect.center
            ),
            key(pygame.K_a, "A"),
            key(pygame.K_3, "3"),
        ]
    )
    assert dialog.draft is before
    assert dialog._web_text_dialog is not None


@pytest.mark.parametrize("mod", [pygame.KMOD_CTRL, pygame.KMOD_ALT, pygame.KMOD_GUI])
@pytest.mark.parametrize(
    "event",
    [
        key(pygame.K_a, "A"),
        key(pygame.K_3, "3"),
        key(pygame.K_DELETE),
        key(pygame.K_RETURN),
        key(pygame.K_KP_ENTER),
        key(pygame.K_TAB),
        key(pygame.K_RIGHT),
    ],
)
def test_command_modifiers_do_not_edit_navigate_or_start(dialog, mod, event):
    dialog._load_preset(0)
    dialog.selected_cell = (0, 0)
    before = dialog.draft, dialog.validation_error, dialog.notice_message
    assert dialog._handle_events([key(event.key, event.unicode, mod)]) is None
    assert (dialog.draft, dialog.validation_error, dialog.notice_message) == before
    assert dialog.selected_cell == (0, 0)
    assert dialog.running


def test_panel_information_uses_info_font_instead_of_board_candidates(dialog):
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

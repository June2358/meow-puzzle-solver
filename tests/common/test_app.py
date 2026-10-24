import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pygame
import pytest

from puzzle_common import app
from puzzle_common.engine import Outcome


@pytest.fixture
def lifecycle(monkeypatch):
    calls = []
    monkeypatch.setattr(pygame, "init", lambda: calls.append("init"))
    monkeypatch.setattr(pygame, "quit", lambda: calls.append("quit"))
    monkeypatch.setattr(pygame.key, "stop_text_input", lambda: None)
    return calls


def editor_sequence(monkeypatch, steps):
    steps = iter(steps)
    received = []

    class Editor:
        def __init__(self, definition, initial_grid=None, initial_error=None):
            received.append((definition.key, initial_grid, initial_error))
            self.result, self.draft, self.quit_requested = next(steps)

        async def run(self):
            return self.result

    monkeypatch.setattr(app, "InputDialog", Editor, raising=False)
    return received


def select_sequence(monkeypatch, keys):
    keys = iter(keys)

    class Selector:
        async def run(self):
            return next(keys)

    monkeypatch.setattr(app, "PuzzleSelector", Selector, raising=False)


def test_switching_puzzles_retains_separate_unsolved_drafts(monkeypatch, lifecycle):
    first, second = (("A",),), ((4,),)
    select_sequence(monkeypatch, ("meow", "sudoku", "meow", None))
    received = editor_sequence(
        monkeypatch,
        ((None, first, False), (None, second, False), (None, first, False)),
    )
    asyncio.run(app.run_app())
    assert received == [
        ("meow", None, None),
        ("sudoku", None, None),
        ("meow", first, None),
    ]
    assert lifecycle == ["init", "quit"]


@pytest.mark.parametrize("outcome", (Outcome.UNIQUE, Outcome.MULTIPLE))
def test_player_returns_to_original_editor_without_reinitializing(
    monkeypatch, lifecycle, outcome
):
    puzzle = object()
    original = (("A",),)
    result = SimpleNamespace(outcome=outcome)
    definition = replace(
        app.DEFINITIONS[0], solve=lambda _: result, grid=lambda _: original
    )
    monkeypatch.setattr(app, "DEFINITIONS", (definition,))
    received = editor_sequence(
        monkeypatch, ((puzzle, original, False), (None, original, True))
    )

    class Player:
        def __init__(self, registered, native, solved):
            assert (registered, native, solved) == (definition, puzzle, result)

        async def run(self):
            return original

    monkeypatch.setattr(app, "PlaybackScreen", Player, raising=False)
    asyncio.run(app.run_app(initial_key=definition.key))
    assert received == [(definition.key, None, None), (definition.key, original, None)]
    assert lifecycle == ["init", "quit"]


def test_unsolvable_result_keeps_draft_and_shows_error(monkeypatch, lifecycle):
    draft = (("A",),)
    definition = replace(
        app.DEFINITIONS[0],
        solve=lambda _: SimpleNamespace(outcome=Outcome.UNSOLVABLE),
        grid=lambda _: draft,
    )
    monkeypatch.setattr(app, "DEFINITIONS", (definition,))
    received = editor_sequence(
        monkeypatch, ((object(), draft, False), (None, draft, True))
    )
    monkeypatch.setattr(
        app,
        "PlaybackScreen",
        lambda *_: pytest.fail("Unsolvable results must return to the editor"),
        raising=False,
    )
    asyncio.run(app.run_app(initial_key=definition.key))
    assert received == [
        (definition.key, None, None),
        (definition.key, draft, app.UNSOLVABLE_MESSAGE),
    ]
    assert lifecycle == ["init", "quit"]


def test_window_close_in_editor_exits_without_selector(monkeypatch, lifecycle):
    editor_sequence(monkeypatch, ((None, (), True),))
    select_sequence(monkeypatch, ())
    asyncio.run(app.run_app(initial_key="meow"))
    assert lifecycle == ["init", "quit"]


def test_return_to_selector_drops_stale_error_and_preserves_changed_draft(
    monkeypatch, lifecycle
):
    original, changed = (("A",),), (("B",),)
    definition = replace(
        app.DEFINITIONS[0],
        solve=lambda _: SimpleNamespace(outcome=Outcome.UNSOLVABLE),
        grid=lambda _: original,
    )
    monkeypatch.setattr(app, "DEFINITIONS", (definition,))
    received = editor_sequence(
        monkeypatch,
        ((object(), original, False), (None, changed, False), (None, changed, True)),
    )
    select_sequence(monkeypatch, (definition.key,))

    asyncio.run(app.run_app(initial_key=definition.key))

    assert received == [
        (definition.key, None, None),
        (definition.key, original, app.UNSOLVABLE_MESSAGE),
        (definition.key, changed, None),
    ]
    assert lifecycle == ["init", "quit"]


def test_invalid_initial_key_is_rejected_before_initialization(lifecycle):
    with pytest.raises(ValueError, match="unknown"):
        asyncio.run(app.run_app(initial_key="unknown"))
    assert lifecycle == []


@pytest.mark.parametrize("stage", ("editor", "solve", "player"))
def test_failure_always_closes_pygame(monkeypatch, lifecycle, stage):
    def fail(*_args, **_kwargs):
        raise RuntimeError(f"{stage} failed")

    definition = replace(
        app.DEFINITIONS[0],
        solve=fail
        if stage == "solve"
        else lambda _: SimpleNamespace(outcome=Outcome.UNIQUE),
        grid=lambda _: (),
    )
    monkeypatch.setattr(app, "DEFINITIONS", (definition,))
    editor_sequence(monkeypatch, ((object(), (), False),))
    if stage == "editor":
        monkeypatch.setattr(app, "InputDialog", fail, raising=False)
    monkeypatch.setattr(app, "PlaybackScreen", fail, raising=False)
    with pytest.raises(RuntimeError, match=f"{stage} failed"):
        asyncio.run(app.run_app(initial_key=definition.key))
    assert lifecycle == ["init", "quit"]


def test_browser_query_is_validated_at_composition_root(monkeypatch):
    import platform

    monkeypatch.setattr(app, "sys", SimpleNamespace(platform="emscripten"))
    location = SimpleNamespace(search="?puzzle=sudoku")
    monkeypatch.setattr(
        platform, "window", SimpleNamespace(location=location), raising=False
    )
    assert app._browser_initial_key() == "sudoku"
    location.search = "?puzzle=unknown"
    assert app._browser_initial_key() is None
    location.search = "?unrelated=sudoku"
    assert app._browser_initial_key() is None


def test_browser_query_is_read_once_across_mode_switches(monkeypatch, lifecycle):
    reads = []

    def browser_key():
        reads.append("read")
        return "meow"

    monkeypatch.setattr(app, "_browser_initial_key", browser_key)
    editor_sequence(monkeypatch, ((None, (), False), (None, (), True)))
    select_sequence(monkeypatch, ("sudoku",))
    asyncio.run(app.run_app())
    assert reads == ["read"]
    assert lifecycle == ["init", "quit"]


def test_player_window_close_exits_without_reopening_editor(monkeypatch, lifecycle):
    definition = replace(
        app.DEFINITIONS[0],
        solve=lambda _: SimpleNamespace(outcome=Outcome.UNIQUE),
        grid=lambda _: (),
    )
    monkeypatch.setattr(app, "DEFINITIONS", (definition,))
    received = editor_sequence(monkeypatch, ((object(), (), False),))

    class Player:
        def __init__(self, *_):
            pass

        async def run(self):
            return None

    monkeypatch.setattr(app, "PlaybackScreen", Player)
    asyncio.run(app.run_app(initial_key=definition.key))
    assert len(received) == 1
    assert lifecycle == ["init", "quit"]


def test_selector_keyboard_mouse_and_window_close():
    pygame.init()
    try:
        selector = app.PuzzleSelector()
        selector.draw()
        assert (
            selector._handle_events(
                [
                    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_DOWN, mod=0),
                    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0),
                ]
            )
            == app.DEFINITIONS[1].key
        )
        assert (
            selector._handle_events(
                [
                    pygame.event.Event(
                        pygame.KEYDOWN, key=pygame.K_TAB, mod=pygame.KMOD_SHIFT
                    ),
                    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0),
                ]
            )
            == app.DEFINITIONS[0].key
        )
        assert (
            selector._handle_events(
                [
                    pygame.event.Event(
                        pygame.MOUSEBUTTONDOWN,
                        button=1,
                        pos=selector.buttons[1].rect.center,
                    )
                ]
            )
            == app.DEFINITIONS[1].key
        )
        assert (
            selector._handle_events(
                [
                    pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, mod=0),
                    pygame.event.Event(pygame.QUIT),
                ]
            )
            == "quit"
        )
    finally:
        pygame.quit()

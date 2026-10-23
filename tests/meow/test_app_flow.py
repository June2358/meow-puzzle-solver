from __future__ import annotations

import asyncio

import pytest

import meow.app as app_module
import puzzle_common.app as shared_app
from meow.model import Puzzle
from meow.presentation import to_playback
from meow.puzzle_catalog import load_preset
from meow.solver import solve


def _disable_pygame(monkeypatch: pytest.MonkeyPatch, lifecycle: list[str]) -> None:
    monkeypatch.setattr(shared_app.pygame, "init", lambda: lifecycle.append("init"))
    monkeypatch.setattr(shared_app.pygame, "quit", lambda: lifecycle.append("quit"))
    monkeypatch.setattr(shared_app.pygame.key, "stop_text_input", lambda: None)


def test_solve_once_then_edit_restores_the_same_region_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []
    _disable_pygame(monkeypatch, lifecycle)
    puzzle = load_preset("극한")
    solved = solve(puzzle)
    dialog_results = iter((puzzle, None))
    dialog_drafts: list[object] = []
    solve_calls: list[object] = []

    class FakeDialog:
        def __init__(self, initial_grid=None, initial_error=None) -> None:
            assert initial_error is None
            dialog_drafts.append(initial_grid)

        async def run(self):
            return next(dialog_results)

    class FakeVisualizer:
        def __init__(self, received_puzzle, received_result) -> None:
            assert received_puzzle is puzzle
            assert received_result == to_playback(solved)

        async def run(self):
            return puzzle.region_grid

    monkeypatch.setattr(app_module, "MeowInputDialog", FakeDialog)
    monkeypatch.setattr(app_module, "MeowVisualizer", FakeVisualizer)
    monkeypatch.setattr(
        app_module,
        "solve",
        lambda received: solve_calls.append(received) or solved,
    )

    asyncio.run(app_module.main())

    assert dialog_drafts == [None, puzzle.region_grid]
    assert solve_calls == [puzzle]
    assert lifecycle == ["init", "quit"]


def test_unsolvable_result_returns_to_editor_with_the_common_message(monkeypatch):
    lifecycle = []
    _disable_pygame(monkeypatch, lifecycle)
    puzzle = Puzzle.from_region_grid((("A", "B"), ("A", "B")))
    results = iter((puzzle, None))
    calls = []

    class FakeDialog:
        def __init__(self, initial_grid=None, initial_error=None):
            calls.append((initial_grid, initial_error))

        async def run(self):
            return next(results)

    def forbidden_player(*args):
        pytest.fail("해 없는 결과는 편집 화면으로 돌아가야 합니다.")

    monkeypatch.setattr(app_module, "MeowInputDialog", FakeDialog)
    monkeypatch.setattr(app_module, "MeowVisualizer", forbidden_player)

    asyncio.run(app_module.main())

    assert calls == [
        (None, None),
        (puzzle.region_grid, shared_app.UNSOLVABLE_MESSAGE),
    ]
    assert lifecycle == ["init", "quit"]

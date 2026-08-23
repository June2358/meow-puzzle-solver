from __future__ import annotations

import asyncio

import pytest

import meow.app as app_module
from meow.puzzle_catalog import load_preset


def _disable_pygame(monkeypatch: pytest.MonkeyPatch, lifecycle: list[str]) -> None:
    monkeypatch.setattr(app_module.pygame, "init", lambda: lifecycle.append("init"))
    monkeypatch.setattr(app_module.pygame, "quit", lambda: lifecycle.append("quit"))
    monkeypatch.setattr(app_module.pygame.key, "stop_text_input", lambda: None)


def test_solve_once_then_edit_restores_the_same_region_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lifecycle: list[str] = []
    _disable_pygame(monkeypatch, lifecycle)
    puzzle = load_preset("극한")
    solved = object()
    dialog_results = iter((puzzle, None))
    dialog_drafts: list[object] = []
    solve_calls: list[object] = []

    class FakeDialog:
        def __init__(self, initial_grid=None) -> None:
            dialog_drafts.append(initial_grid)

        async def run(self):
            return next(dialog_results)

    class FakeVisualizer:
        def __init__(self, received_puzzle, received_result) -> None:
            assert received_puzzle is puzzle
            assert received_result is solved

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

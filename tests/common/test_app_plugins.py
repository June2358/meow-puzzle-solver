import asyncio
from dataclasses import replace

import pygame
import pytest

from puzzle_common import app
from puzzle_common.engine import SolveResult


@pytest.mark.parametrize(
    "registered", app.DEFINITIONS, ids=lambda definition: definition.key
)
def test_real_definitions_use_one_editor_player_and_native_solver(
    monkeypatch, registered
):
    grid = next(iter(registered.presets.values()))
    puzzle = registered.create(grid)
    expected = registered.solve(puzzle)
    assert isinstance(expected, SolveResult)
    drafts, received, lifecycle, solved = [], [], [], []
    inputs = iter((puzzle, None))

    def solve(native):
        result = registered.solve(native)
        solved.append(result)
        return result

    definition = replace(registered, solve=solve)
    monkeypatch.setattr(app, "DEFINITIONS", (definition,))

    class Editor:
        def __init__(self, selected, initial_grid, initial_error):
            assert selected is definition
            drafts.append((initial_grid, initial_error))
            self.draft = grid
            self.quit_requested = False

        async def run(self):
            native = next(inputs)
            self.quit_requested = native is None
            return native

    class Player:
        def __init__(self, selected, native, result):
            assert selected is definition
            received.append((native, result))

        async def run(self):
            return grid

    monkeypatch.setattr(app, "InputDialog", Editor)
    monkeypatch.setattr(app, "PlaybackScreen", Player)
    monkeypatch.setattr(pygame, "init", lambda: lifecycle.append("init"))
    monkeypatch.setattr(pygame, "quit", lambda: lifecycle.append("quit"))
    monkeypatch.setattr(pygame.key, "stop_text_input", lambda: None)
    asyncio.run(app.run_app(initial_key=registered.key))

    assert drafts == [(None, None), (grid, None)]
    assert received == [(puzzle, expected)]
    assert received[0][1] is solved[0]
    assert lifecycle == ["init", "quit"]

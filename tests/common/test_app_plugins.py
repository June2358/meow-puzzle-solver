import asyncio
from dataclasses import replace

import pygame
import pytest

from puzzle_common.app import PuzzlePlugin, run_app
from puzzle_common.engine import SolveResult


@pytest.fixture(params=["meow", "sudoku"])
def plugin_case(request):
    if request.param == "meow":
        from meow.app import PLUGIN
        from meow.puzzle_catalog import load_preset

        puzzle = load_preset("쉬움")
    else:
        from sudoku.app import PLUGIN
        from sudoku.board import Puzzle
        from sudoku.puzzle_catalog import load_puzzle_catalog

        puzzle = Puzzle(load_puzzle_catalog()["쉬움"])
    return PLUGIN, puzzle


def test_registered_puzzles_use_the_same_flow_and_preserve_the_draft(
    plugin_case, monkeypatch
):
    plugin, puzzle = plugin_case
    assert isinstance(plugin, PuzzlePlugin)
    expected = plugin.solve(puzzle)
    assert isinstance(expected, SolveResult)
    inputs = iter((puzzle, None))
    drafts, received, lifecycle, solved = [], [], [], []

    def solve(puzzle_arg):
        result = plugin.solve(puzzle_arg)
        solved.append(result)
        return result

    class Editor:
        def __init__(self, draft, error):
            drafts.append((draft, error))

        async def run(self):
            return next(inputs)

    class Player:
        def __init__(self, puzzle_arg, data):
            received.append((puzzle_arg, data))

        async def run(self):
            return plugin.get_draft(puzzle)

    monkeypatch.setattr(pygame, "init", lambda: lifecycle.append("init"))
    monkeypatch.setattr(pygame, "quit", lambda: lifecycle.append("quit"))
    monkeypatch.setattr(pygame.key, "stop_text_input", lambda: None)
    asyncio.run(
        run_app(
            replace(plugin, create_editor=Editor, create_player=Player, solve=solve)
        )
    )

    assert drafts == [(None, None), (plugin.get_draft(puzzle), None)]
    assert received == [(puzzle, expected)]
    assert received[0][1] is solved[0]
    assert lifecycle == ["init", "quit"]

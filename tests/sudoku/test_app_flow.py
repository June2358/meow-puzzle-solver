import asyncio
from collections.abc import Iterator
from dataclasses import replace

import pytest
from sample_puzzles import UNIQUE_GRID, UNIQUE_SOLUTION

import puzzle_common.app as shared_app
import sudoku.app as app_module
from sudoku.board import Puzzle
from sudoku.presentation import to_playback
from sudoku.solve_types import SolveResult, SolveStatus, SolveStep, StepKind


def result_with_status(puzzle: Puzzle, status: SolveStatus) -> SolveResult:
    def candidates(grid):
        return tuple(
            tuple(
                frozenset({value}) if value else frozenset(range(1, 10))
                for value in row
            )
            for row in grid
        )

    terminal_grid = (
        UNIQUE_SOLUTION if status is not SolveStatus.UNSOLVABLE else puzzle.grid
    )
    terminal_kind = (
        StepKind.UNSOLVABLE if status is SolveStatus.UNSOLVABLE else StepKind.SOLVED
    )
    return SolveResult(
        status=status,
        steps=(
            SolveStep(
                kind=StepKind.INITIAL_STATE,
                grid=puzzle.grid,
                candidates=candidates(puzzle.grid),
            ),
            SolveStep(
                kind=terminal_kind,
                grid=terminal_grid,
                candidates=candidates(terminal_grid),
            ),
        ),
    )


def test_unsolvable_result_returns_to_editor_with_specific_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    puzzle = Puzzle(UNIQUE_GRID)
    dialog_results: Iterator[Puzzle | None] = iter((puzzle, None))
    dialog_calls: list[dict[str, object]] = []
    visualizer_calls: list[object] = []
    quit_calls: list[None] = []

    class FakeDialog:
        def __init__(self, initial_board=None, initial_error=None) -> None:
            dialog_calls.append(
                dict(initial_board=initial_board, initial_error=initial_error)
            )

        async def run(self) -> Puzzle | None:
            return next(dialog_results)

    class FakeSolver:
        def __init__(self, received: Puzzle) -> None:
            assert received is puzzle

        def solve(self) -> SolveResult:
            return result_with_status(puzzle, SolveStatus.UNSOLVABLE)

    class ForbiddenVisualizer:
        def __init__(self, *args: object, **kwargs: object) -> None:
            visualizer_calls.append((args, kwargs))

    plugin = replace(
        app_module.PLUGIN,
        create_editor=FakeDialog,
        solve=lambda puzzle: to_playback(FakeSolver(puzzle).solve()),
        create_player=ForbiddenVisualizer,
    )
    monkeypatch.setattr(shared_app.pygame, "init", lambda: None)
    monkeypatch.setattr(shared_app.pygame.key, "stop_text_input", lambda: None)
    monkeypatch.setattr(shared_app.pygame, "quit", lambda: quit_calls.append(None))

    asyncio.run(shared_app.run_app(plugin))

    assert len(dialog_calls) == 2
    assert dialog_calls[1]["initial_error"] == shared_app.UNSOLVABLE_MESSAGE
    assert dialog_calls[1]["initial_board"] == puzzle.grid
    assert not visualizer_calls
    assert quit_calls == [None]


def test_solved_result_opens_visualizer_and_edit_returns_same_draft(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    puzzle = Puzzle(UNIQUE_GRID)
    dialog_results: Iterator[Puzzle | None] = iter((puzzle, None))
    dialog_calls: list[dict[str, object]] = []
    visualizer_calls: list[tuple[object, ...]] = []
    quit_calls: list[None] = []

    class FakeDialog:
        def __init__(self, initial_board=None, initial_error=None) -> None:
            dialog_calls.append(
                dict(initial_board=initial_board, initial_error=initial_error)
            )

        async def run(self) -> Puzzle | None:
            return next(dialog_results)

    solved_result = result_with_status(puzzle, SolveStatus.SOLVED_MULTIPLE)

    class FakeSolver:
        def __init__(self, received: Puzzle) -> None:
            assert received is puzzle

        def solve(self) -> SolveResult:
            return solved_result

    class FakeVisualizer:
        def __init__(self, *args: object, **kwargs: object) -> None:
            visualizer_calls.append(args)

        async def run(self):
            return puzzle.grid

    plugin = replace(
        app_module.PLUGIN,
        create_editor=FakeDialog,
        solve=lambda puzzle: to_playback(FakeSolver(puzzle).solve()),
        create_player=FakeVisualizer,
    )
    monkeypatch.setattr(shared_app.pygame, "init", lambda: None)
    monkeypatch.setattr(shared_app.pygame.key, "stop_text_input", lambda: None)
    monkeypatch.setattr(shared_app.pygame, "quit", lambda: quit_calls.append(None))

    asyncio.run(shared_app.run_app(plugin))

    assert len(visualizer_calls) == 1
    assert visualizer_calls[0] == (puzzle, to_playback(solved_result))
    assert dialog_calls[1]["initial_board"] == puzzle.grid
    assert dialog_calls[1]["initial_error"] is None
    assert quit_calls == [None]


def test_pygame_quits_when_async_screen_flow_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    quit_calls: list[None] = []

    class FailingDialog:
        def __init__(self, *args: object) -> None:
            pass

        async def run(self) -> Puzzle | None:
            raise RuntimeError("screen failed")

    plugin = replace(app_module.PLUGIN, create_editor=FailingDialog)
    monkeypatch.setattr(shared_app.pygame, "init", lambda: None)
    monkeypatch.setattr(shared_app.pygame.key, "stop_text_input", lambda: None)
    monkeypatch.setattr(shared_app.pygame, "quit", lambda: quit_calls.append(None))

    with pytest.raises(RuntimeError, match="screen failed"):
        asyncio.run(shared_app.run_app(plugin))

    assert quit_calls == [None]

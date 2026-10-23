import asyncio
from collections.abc import Iterator

import pytest
from sample_puzzles import UNIQUE_GRID, UNIQUE_SOLUTION

import sudoku.app as app_module
from sudoku.board import Puzzle
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
        def __init__(self, **kwargs: object) -> None:
            dialog_calls.append(kwargs)

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

    monkeypatch.setattr(app_module, "SudokuInputDialog", FakeDialog)
    monkeypatch.setattr(app_module, "SudokuSolver", FakeSolver)
    monkeypatch.setattr(app_module, "SudokuVisualizer", ForbiddenVisualizer)
    monkeypatch.setattr(app_module.pygame, "init", lambda: None)
    monkeypatch.setattr(app_module.pygame.key, "stop_text_input", lambda: None)
    monkeypatch.setattr(app_module.pygame, "quit", lambda: quit_calls.append(None))

    asyncio.run(app_module.main())

    assert len(dialog_calls) == 2
    assert "가능한 해가 없습니다" in str(dialog_calls[1]["initial_error"])
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
        def __init__(self, **kwargs: object) -> None:
            dialog_calls.append(kwargs)

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

    monkeypatch.setattr(app_module, "SudokuInputDialog", FakeDialog)
    monkeypatch.setattr(app_module, "SudokuSolver", FakeSolver)
    monkeypatch.setattr(app_module, "SudokuVisualizer", FakeVisualizer)
    monkeypatch.setattr(app_module.pygame, "init", lambda: None)
    monkeypatch.setattr(app_module.pygame.key, "stop_text_input", lambda: None)
    monkeypatch.setattr(app_module.pygame, "quit", lambda: quit_calls.append(None))

    asyncio.run(app_module.main())

    assert len(visualizer_calls) == 1
    assert visualizer_calls[0] == (puzzle, solved_result)
    assert dialog_calls[1]["initial_board"] == puzzle.grid
    assert dialog_calls[1]["initial_error"] is None
    assert quit_calls == [None]


def test_pygame_quits_when_async_screen_flow_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    quit_calls: list[None] = []

    class FailingDialog:
        def __init__(self, **kwargs: object) -> None:
            pass

        async def run(self) -> Puzzle | None:
            raise RuntimeError("screen failed")

    monkeypatch.setattr(app_module, "SudokuInputDialog", FailingDialog)
    monkeypatch.setattr(app_module.pygame, "init", lambda: None)
    monkeypatch.setattr(app_module.pygame.key, "stop_text_input", lambda: None)
    monkeypatch.setattr(app_module.pygame, "quit", lambda: quit_calls.append(None))

    with pytest.raises(RuntimeError, match="screen failed"):
        asyncio.run(app_module.main())

    assert quit_calls == [None]

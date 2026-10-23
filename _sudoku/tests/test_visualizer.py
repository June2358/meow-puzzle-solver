import asyncio

import pygame
import pytest
from sample_puzzles import UNIQUE_GRID

from sudoku.board import Puzzle
from sudoku.solve_types import SolveResult
from sudoku.solver import SudokuSolver
from sudoku.visualizer import (
    _AUTOPLAY_INTERVAL,
    _NAVIGATION_REPEAT_DELAY,
    _NAVIGATION_REPEAT_INTERVAL,
    SudokuVisualizer,
)


@pytest.fixture(scope="module")
def solved_case() -> tuple[Puzzle, SolveResult]:
    puzzle = Puzzle(UNIQUE_GRID)
    return puzzle, SudokuSolver(puzzle).solve()


@pytest.fixture(autouse=True)
def pygame_display() -> None:
    pygame.init()
    yield
    pygame.display.quit()


def test_visualizer_draws_a_solved_result(
    solved_case: tuple[Puzzle, SolveResult],
) -> None:
    visualizer = SudokuVisualizer(*solved_case)

    assert visualizer.screen.get_size() == (940, 640)
    visualizer.draw()


def test_visualizer_navigation_stays_within_the_trace(
    solved_case: tuple[Puzzle, SolveResult],
) -> None:
    visualizer = SudokuVisualizer(*solved_case)

    assert not visualizer._navigate(-1)
    assert visualizer._navigate(1)
    visualizer._set_index(10_000)
    assert visualizer.current_step_index == len(visualizer.result.steps) - 1
    assert not visualizer._navigate(1)


def test_held_arrow_key_repeats_and_stops_on_release(
    solved_case: tuple[Puzzle, SolveResult],
) -> None:
    visualizer = SudokuVisualizer(*solved_case)
    visualizer._set_index(1)

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
    visualizer._handle_events(pygame.event.get())
    assert visualizer.current_step_index == 2

    visualizer._update_navigation_hold(_NAVIGATION_REPEAT_DELAY + 0.001)
    assert visualizer.current_step_index == 3

    visualizer._update_navigation_hold(_NAVIGATION_REPEAT_INTERVAL * 2)
    assert visualizer.current_step_index == 5

    pygame.event.post(pygame.event.Event(pygame.KEYUP, key=pygame.K_RIGHT))
    visualizer._handle_events(pygame.event.get())
    visualizer._update_navigation_hold(
        _NAVIGATION_REPEAT_DELAY + _NAVIGATION_REPEAT_INTERVAL
    )
    assert visualizer.current_step_index == 5


def test_home_end_and_autoplay_navigation(
    solved_case: tuple[Puzzle, SolveResult],
) -> None:
    visualizer = SudokuVisualizer(*solved_case)

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END))
    visualizer._handle_events(pygame.event.get())
    assert visualizer.current_step_index == len(visualizer.result.steps) - 1

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_HOME))
    visualizer._handle_events(pygame.event.get())
    assert visualizer.current_step_index == 0

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    visualizer._handle_events(pygame.event.get())
    visualizer._update_autoplay(_AUTOPLAY_INTERVAL)
    assert visualizer.current_step_index == 1


def test_run_yields_a_frame_then_handles_a_quit_event(
    solved_case: tuple[Puzzle, SolveResult],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visualizer = SudokuVisualizer(*solved_case)
    draw_calls: list[None] = []
    frame_calls: list[pygame.time.Clock] = []

    monkeypatch.setattr(visualizer, "draw", lambda: draw_calls.append(None))

    async def advance_frame(clock: pygame.time.Clock) -> float:
        frame_calls.append(clock)
        await asyncio.sleep(0)
        return 1 / 60

    monkeypatch.setattr("sudoku.visualizer.next_frame", advance_frame)
    monkeypatch.setattr(
        pygame.event,
        "get",
        lambda: [pygame.event.Event(pygame.QUIT)],
    )

    assert asyncio.run(visualizer.run()) is None
    assert draw_calls == [None]
    assert len(frame_calls) == 1

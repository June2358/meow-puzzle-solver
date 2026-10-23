import asyncio
from dataclasses import replace
from unittest.mock import Mock

import pygame
import pytest
from sample_puzzles import UNIQUE_GRID, UNIQUE_SOLUTION

from puzzle_common.playback import (
    _AUTOPLAY_INTERVAL,
    _NAVIGATION_REPEAT_DELAY,
    _NAVIGATION_REPEAT_INTERVAL,
)
from puzzle_common.presentation import PlaybackData
from puzzle_common.ui_style import wrap_text
from sudoku.board import Puzzle
from sudoku.presentation import to_playback
from sudoku.puzzle_catalog import load_puzzle_catalog
from sudoku.solve_types import SolveStep
from sudoku.solver import SudokuSolver
from sudoku.visualizer import SudokuVisualizer


@pytest.fixture(scope="module")
def solved_case() -> tuple[Puzzle, PlaybackData[SolveStep]]:
    puzzle = Puzzle(UNIQUE_GRID)
    return puzzle, to_playback(SudokuSolver(puzzle).solve())


@pytest.fixture(autouse=True)
def pygame_display() -> None:
    pygame.init()
    yield
    pygame.display.quit()


def test_visualizer_draws_a_solved_result(
    solved_case: tuple[Puzzle, PlaybackData[SolveStep]],
) -> None:
    visualizer = SudokuVisualizer(*solved_case)

    assert visualizer.screen.get_size() == (1010, 700)
    visualizer.draw()


def test_visualizer_can_render_a_normalized_unsolvable_trace() -> None:
    grid = [list(row) for row in UNIQUE_SOLUTION]
    grid[0][0], grid[0][7], grid[2][0] = 1, 0, 0
    puzzle = Puzzle(grid)
    data = to_playback(SudokuSolver(puzzle).solve())
    visualizer = SudokuVisualizer(puzzle, data)

    visualizer._set_index(visualizer.frame_count - 1)
    visualizer.draw()

    assert "해 없음" in visualizer._status_badge()[0]
    assert visualizer._presentation(visualizer.current_frame).title == "해 없음"


def test_visualizer_navigation_stays_within_the_trace(
    solved_case: tuple[Puzzle, PlaybackData[SolveStep]],
) -> None:
    visualizer = SudokuVisualizer(*solved_case)

    assert not visualizer._navigate(-1)
    assert visualizer._navigate(1)
    visualizer._set_index(10_000)
    assert visualizer.current_step_index == len(visualizer.frames) - 1
    assert not visualizer._navigate(1)


def test_presentation_keeps_assumption_reason_and_structured_effects() -> None:
    puzzle = Puzzle(load_puzzle_catalog()["극한"])
    visualizer = SudokuVisualizer(puzzle, to_playback(SudokuSolver(puzzle).solve()))
    visualizer.current_step_index = 6

    details = visualizer._presentation(visualizer.current_frame)

    assert details.title == "논리 기법"
    assert details.reason == "표시된 칸에 가능한 후보가 하나뿐입니다."
    assert details.effects == (("확정 칸 · 1", ("R2C7 = 5",)),)
    assert details.assumption == "R2C3 = 1"
    assert [text for text, _ in details.annotations] == [
        "Naked Single",
        "한 단계 가정 중",
    ]
    visualizer.draw()


def test_multiple_solution_warning_and_last_digit_label() -> None:
    grid = [list(row) for row in UNIQUE_SOLUTION]
    for row, col in ((0, 3), (0, 4), (3, 3), (3, 4)):
        grid[row][col] = 0
    puzzle = Puzzle(grid)
    visualizer = SudokuVisualizer(puzzle, to_playback(SudokuSolver(puzzle).solve()))

    assert "복수해" in visualizer._status_badge()[0]
    visualizer.current_step_index = next(
        index
        for index, step in enumerate(visualizer.frames)
        if step.deduction is not None
        and all(value for row in step.grid for value in row)
    )
    details = visualizer._presentation(visualizer.current_frame)
    assert details.annotations[0][0] == "Last Digit"
    visualizer.draw()


@pytest.mark.parametrize("step_index", (2, 3))
def test_multiple_solution_reason_remains_visible_during_assumption(step_index) -> None:
    grid = [list(row) for row in UNIQUE_SOLUTION]
    for row, col in ((0, 3), (0, 4), (3, 3), (3, 4)):
        grid[row][col] = 0
    puzzle = Puzzle(grid)
    visualizer = SudokuVisualizer(puzzle, to_playback(SudokuSolver(puzzle).solve()))
    visualizer.current_step_index = step_index
    details = visualizer._presentation(visualizer.current_frame)
    reason_lines = wrap_text(
        details.reason, visualizer.fonts.body, visualizer.panel_rect.width - 36
    )
    assert len(reason_lines) >= 1
    body = Mock(wraps=visualizer.fonts.body)
    visualizer.fonts = replace(visualizer.fonts, body=body)

    visualizer.draw()

    rendered = [call.args[0] for call in body.render.call_args_list]
    assert all(line in rendered for line in reason_lines)
    assert any(details.assumption in line for line in rendered)
    assert all(
        any(item in line for line in rendered)
        for _, items in details.effects
        for item in items
    )


def test_removed_candidate_has_a_red_strike(
    solved_case: tuple[Puzzle, PlaybackData[SolveStep]],
) -> None:
    visualizer = SudokuVisualizer(*solved_case)
    visualizer.screen.fill((255, 255, 255))

    visualizer._draw_candidate_marks(0, 2, frozenset({1}), frozenset({5}))

    center = visualizer.layout.cell_rect((0, 2)).center
    assert tuple(visualizer.screen.get_at((center[0] - 4, center[1]))[:3]) == (
        220,
        38,
        38,
    )


def test_held_arrow_key_repeats_and_stops_on_release(
    solved_case: tuple[Puzzle, PlaybackData[SolveStep]],
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
    solved_case: tuple[Puzzle, PlaybackData[SolveStep]],
) -> None:
    visualizer = SudokuVisualizer(*solved_case)

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END))
    visualizer._handle_events(pygame.event.get())
    assert visualizer.current_step_index == len(visualizer.frames) - 1

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_HOME))
    visualizer._handle_events(pygame.event.get())
    assert visualizer.current_step_index == 0

    pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
    visualizer._handle_events(pygame.event.get())
    visualizer._update_autoplay(_AUTOPLAY_INTERVAL)
    assert visualizer.current_step_index == 1


def test_run_yields_a_frame_then_handles_a_quit_event(
    solved_case: tuple[Puzzle, PlaybackData[SolveStep]],
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

    monkeypatch.setattr("puzzle_common.playback.next_frame", advance_frame)
    monkeypatch.setattr(
        pygame.event,
        "get",
        lambda: [pygame.event.Event(pygame.QUIT)],
    )

    assert asyncio.run(visualizer.run()) is None
    assert draw_calls == [None]
    assert len(frame_calls) == 1

"""The same playback contract runs against both real puzzle adapters."""

import asyncio

import pygame
import pytest
from sample_puzzles import UNIQUE_GRID

from meow.puzzle_catalog import load_preset
from meow.solver import solve
from meow.visualizer import MeowVisualizer
from sudoku.board import Puzzle
from sudoku.solver import SudokuSolver
from sudoku.visualizer import SudokuVisualizer


@pytest.fixture(params=("regions", "digits"))
def playback(request):
    pygame.init()
    if request.param == "regions":
        puzzle = load_preset("쉬움")
        visualizer = MeowVisualizer(puzzle, solve(puzzle))
    else:
        puzzle = Puzzle(UNIQUE_GRID)
        visualizer = SudokuVisualizer(puzzle, SudokuSolver(puzzle).solve())
    yield visualizer
    pygame.display.quit()


def key(kind, value):
    return pygame.event.Event(kind, key=value)


def test_hold_ignores_os_repeat_then_uses_elapsed_time(playback):
    playback._handle_events([key(pygame.KEYDOWN, pygame.K_RIGHT)])
    playback._handle_events([key(pygame.KEYDOWN, pygame.K_RIGHT)])
    assert playback.current_step_index == 1
    playback._update_navigation_hold(0.359)
    assert playback.current_step_index == 1
    playback._update_navigation_hold(0.002)
    assert playback.current_step_index == 2
    playback._update_navigation_hold(0.16)
    assert playback.current_step_index == 4
    playback._handle_events([key(pygame.KEYUP, pygame.K_RIGHT)])
    playback._update_navigation_hold(1)
    assert playback.current_step_index == 4


def test_releasing_newest_hold_resumes_older_direction_after_delay(playback):
    playback._set_index(4)
    playback._handle_events([key(pygame.KEYDOWN, pygame.K_RIGHT)])
    playback._handle_events([key(pygame.KEYDOWN, pygame.K_LEFT)])
    assert playback.current_step_index == 4
    playback._update_navigation_hold(0.361)
    assert playback.current_step_index == 3
    playback._handle_events([key(pygame.KEYUP, pygame.K_LEFT)])
    playback._update_navigation_hold(0.359)
    assert playback.current_step_index == 3
    playback._update_navigation_hold(0.002)
    assert playback.current_step_index == 4


def test_releasing_older_hold_keeps_newest_repeat_timer(playback):
    playback._set_index(4)
    playback._handle_events([key(pygame.KEYDOWN, pygame.K_RIGHT)])
    playback._handle_events([key(pygame.KEYDOWN, pygame.K_LEFT)])
    playback._update_navigation_hold(0.3)
    playback._handle_events([key(pygame.KEYUP, pygame.K_RIGHT)])
    playback._update_navigation_hold(0.061)
    assert playback.current_step_index == 3


def test_mouse_hold_repeats_until_release_or_focus_loss(playback):
    down = pygame.event.Event(
        pygame.MOUSEBUTTONDOWN, button=1, pos=playback.next_button.rect.center
    )
    playback._handle_events([down])
    playback._update_navigation_hold(0.441)
    assert playback.current_step_index == 3
    playback._handle_events([pygame.event.Event(pygame.MOUSEBUTTONUP, button=1)])
    playback._update_navigation_hold(1)
    assert playback.current_step_index == 3
    playback._handle_events([down, pygame.event.Event(pygame.WINDOWFOCUSLOST)])
    playback._update_navigation_hold(1)
    assert playback.current_step_index == 4
    assert not playback._held_navigation_sources


@pytest.mark.parametrize("jump", (pygame.K_HOME, pygame.K_END))
def test_home_end_cancel_held_navigation(playback, jump):
    playback._set_index(4)
    playback._handle_events([key(pygame.KEYDOWN, pygame.K_LEFT)])
    playback._handle_events([key(pygame.KEYDOWN, jump)])
    playback._update_navigation_hold(1)
    expected = playback.frame_count - 1 if jump == pygame.K_END else 0
    assert playback.current_step_index == expected
    assert not playback._held_navigation_sources


def test_autoplay_stops_as_soon_as_it_reaches_last_step(playback):
    playback._set_index(10_000)
    last_index = playback.current_step_index
    playback._navigate(-1)
    playback._toggle_autoplay()
    assert playback._update_autoplay(0.9)
    assert playback.current_step_index == last_index
    assert not playback.autoplay_enabled
    playback._toggle_autoplay()
    assert playback.current_step_index == 0
    assert playback.autoplay_enabled


def test_switching_from_hold_to_play_does_not_spend_elapsed_time_twice(
    playback, monkeypatch
):
    playback._handle_events([key(pygame.KEYDOWN, pygame.K_RIGHT)])
    events = iter(
        ([key(pygame.KEYDOWN, pygame.K_SPACE)], [key(pygame.KEYDOWN, pygame.K_ESCAPE)])
    )

    async def advance_frame(clock):
        await asyncio.sleep(0)
        return 1.0

    monkeypatch.setattr("puzzle_common.playback.next_frame", advance_frame)
    monkeypatch.setattr(pygame.event, "get", lambda: next(events))

    asyncio.run(playback.run())

    assert playback.current_step_index == 1


@pytest.mark.parametrize("trigger", ("escape", "button"))
def test_run_returns_original_draft_on_edit(playback, monkeypatch, trigger):
    original = (
        playback.puzzle.region_grid
        if isinstance(playback, MeowVisualizer)
        else playback.puzzle.grid
    )
    event = (
        key(pygame.KEYDOWN, pygame.K_ESCAPE)
        if trigger == "escape"
        else pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=playback.edit_button.rect.center
        )
    )
    monkeypatch.setattr(pygame.event, "get", lambda: [event])
    assert asyncio.run(playback.run()) is original

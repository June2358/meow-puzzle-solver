"""The same playback contract runs against both real puzzle adapters."""

import asyncio
from dataclasses import replace

import pygame
import pytest
from sample_puzzles import UNIQUE_GRID, UNIQUE_SOLUTION

from meow.definition import DEFINITION as MEOW
from meow.definition import PRESET_NAMES, load_preset
from meow.model import Puzzle as MeowPuzzle
from meow.solver import solve
from puzzle_common.engine import Outcome
from puzzle_common.playback import PlaybackScreen
from puzzle_common.ui_style import (
    ACCENT,
    ACCENT_LIGHT,
    ORANGE,
    ORANGE_LIGHT,
    RED,
    RED_LIGHT,
)
from sudoku.board import Puzzle
from sudoku.definition import DEFINITION as SUDOKU
from sudoku.definition import load_puzzle_catalog
from sudoku.solver import solve as solve_sudoku


@pytest.fixture(params=("regions", "digits"))
def playback(request):
    pygame.init()
    if request.param == "regions":
        puzzle = load_preset("쉬움")
        visualizer = PlaybackScreen(MEOW, puzzle.region_grid, solve(puzzle))
    else:
        puzzle = Puzzle(UNIQUE_GRID)
        visualizer = PlaybackScreen(SUDOKU, puzzle.grid, solve_sudoku(puzzle))
    yield visualizer
    pygame.display.quit()


def key(kind, value):
    return pygame.event.Event(kind, key=value)


@pytest.mark.parametrize("trigger", ["escape", "button"])
def test_close_request_wins_over_queued_return_to_editor(playback, trigger):
    event = (
        key(pygame.KEYDOWN, pygame.K_ESCAPE)
        if trigger == "escape"
        else pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=playback.edit_button.rect.center
        )
    )
    assert playback._handle_events([event, pygame.event.Event(pygame.QUIT)]) is None
    assert not playback.running


@pytest.mark.parametrize(
    "outcome, expected",
    (
        (Outcome.UNIQUE, ("유일해", ACCENT, ACCENT_LIGHT)),
        (Outcome.MULTIPLE, ("복수해 · 가능한 해 중 하나 표시", ORANGE, ORANGE_LIGHT)),
        (Outcome.UNSOLVABLE, ("해 없음 · 유효한 배치 없음", RED, RED_LIGHT)),
    ),
)
def test_common_outcome_badges_render_for_both_puzzles(playback, outcome, expected):
    if outcome is Outcome.UNIQUE:
        visualizer = playback
    elif playback.definition.key == "meow":
        size = 4 if outcome is Outcome.MULTIPLE else 2
        puzzle = MeowPuzzle.from_region_grid(
            tuple(tuple("ABCD"[:size]) for _ in range(size))
        )
        visualizer = PlaybackScreen(MEOW, puzzle.region_grid, solve(puzzle))
    else:
        grid = [list(row) for row in UNIQUE_SOLUTION]
        if outcome is Outcome.MULTIPLE:
            for row, col in ((0, 3), (0, 4), (3, 3), (3, 4)):
                grid[row][col] = 0
        else:
            grid[0][0] = 1
            grid[0][7] = grid[2][0] = 0
        puzzle = Puzzle(grid)
        visualizer = PlaybackScreen(SUDOKU, puzzle.grid, solve_sudoku(puzzle))
    assert visualizer.outcome is outcome
    assert visualizer._status_badge() == expected
    assert type(visualizer)._status_badge is PlaybackScreen._status_badge
    visualizer.draw()


def test_visualizers_reject_nonresults_and_foreign_snapshots(playback):
    with pytest.raises(TypeError, match="SolveResult"):
        PlaybackScreen(playback.definition, playback.grid, object())
    if playback.definition.key == "meow":
        foreign = solve_sudoku(Puzzle(UNIQUE_GRID))
    else:
        foreign = solve(load_preset("쉬움"))
    with pytest.raises(TypeError):
        PlaybackScreen(playback.definition, playback.grid, foreign)
    bad = replace(
        playback.result.run.initial_logic_result,
        initial_state=object(),
        final_state=object(),
    )
    result = replace(
        playback.result, run=replace(playback.result.run, initial_logic_result=bad)
    )
    with pytest.raises(TypeError):
        PlaybackScreen(playback.definition, playback.grid, result)


def test_visualizers_reject_another_puzzles_trace(playback):
    if playback.definition.key == "meow":
        other = load_preset("보통").region_grid
    else:
        other = tuple((0,) * 9 for _ in range(9))
    with pytest.raises(ValueError, match="전달된 문제"):
        PlaybackScreen(playback.definition, other, playback.result)


def test_draw_delivers_the_exact_current_frame_to_both_hooks(playback, monkeypatch):
    delivered = []
    original_presentation = playback._presentation
    monkeypatch.setattr(playback, "_draw_board", lambda frame: delivered.append(frame))

    def presentation(frame):
        delivered.append(frame)
        return original_presentation(frame)

    monkeypatch.setattr(playback, "_presentation", presentation)
    playback._set_index(2)
    playback.draw()

    assert len(delivered) == 2
    assert delivered[0] is delivered[1] is playback.current_frame


@pytest.mark.parametrize("app", ("regions", "digits"))
def test_all_builtin_frames_render_effects_within_the_details_area(app, monkeypatch):
    pygame.init()
    puzzles = (
        [load_preset(name) for name in PRESET_NAMES]
        if app == "regions"
        else [Puzzle(grid) for grid in load_puzzle_catalog().values()]
    )
    for puzzle in puzzles:
        view = (
            PlaybackScreen(MEOW, puzzle.region_grid, solve(puzzle))
            if app == "regions"
            else PlaybackScreen(SUDOKU, puzzle.grid, solve_sudoku(puzzle))
        )
        draw_effects = view._draw_effect_items
        visible_groups = []

        def check_effects(
            items,
            x,
            y,
            *,
            draw_effects=draw_effects,
            visible_groups=visible_groups,
            **kwargs,
        ):
            bottom = draw_effects(items, x, y, **kwargs)
            assert y < bottom <= kwargs["max_y"]
            visible_groups.append(items)
            return bottom

        monkeypatch.setattr(view, "_draw_effect_items", check_effects)
        for index, frame in enumerate(view.frames):
            view._set_index(index)
            visible_groups.clear()
            view.draw()
            assert visible_groups == [
                items for _, items in view._presentation(frame).effects
            ]
    pygame.display.quit()


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


@pytest.mark.parametrize("trigger", ("escape", "button", "quit"))
def test_run_returns_edit_or_close_action(playback, monkeypatch, trigger):
    event = (
        key(pygame.KEYDOWN, pygame.K_ESCAPE)
        if trigger == "escape"
        else pygame.event.Event(pygame.QUIT)
        if trigger == "quit"
        else pygame.event.Event(
            pygame.MOUSEBUTTONDOWN, button=1, pos=playback.edit_button.rect.center
        )
    )
    monkeypatch.setattr(pygame.event, "get", lambda: [event])
    assert asyncio.run(playback.run()) is (trigger != "quit")

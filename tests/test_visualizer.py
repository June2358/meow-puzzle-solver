from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from meow.exact_solver import ExactStatus
from meow.model import Puzzle
from meow.puzzle_catalog import load_preset
from meow.solver import solve
from meow.timeline import TimelineKind
from meow.visualizer import MeowVisualizer

MULTIPLE_GRID = (
    ("A", "B", "C", "D"),
    ("A", "B", "C", "D"),
    ("A", "B", "C", "D"),
    ("A", "B", "C", "D"),
)
UNSOLVABLE_GRID = (
    ("A", "B"),
    ("A", "B"),
)


@pytest.fixture(scope="module", autouse=True)
def pygame_dummy_display():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


def test_core_frames_render_and_navigation_repeats_while_held() -> None:
    puzzle = load_preset("극한")
    visualizer = MeowVisualizer(puzzle, solve(puzzle))
    core_kinds = (
        TimelineKind.LOGIC_STEP,
        TimelineKind.ASSUME,
        TimelineKind.RESTORE,
        TimelineKind.BACKTRACKING,
        TimelineKind.FINAL,
    )

    for kind in core_kinds:
        visualizer.current_step_index = next(
            index
            for index, frame in enumerate(visualizer.timeline)
            if frame.kind is kind
        )
        visualizer.draw()

    visualizer.current_step_index = 0
    source = ("key", pygame.K_RIGHT)
    visualizer._begin_navigation_hold(source, 1)
    assert visualizer.current_step_index == 1

    visualizer._update_navigation_hold(0.37)
    assert visualizer.current_step_index == 2

    visualizer._end_navigation_hold(source)
    visualizer._update_navigation_hold(1.0)
    assert visualizer.current_step_index == 2

    visualizer._toggle_autoplay()
    visualizer._update_autoplay(0.91)
    assert visualizer.current_step_index == 3

    visualizer._handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_END))
    assert visualizer.current_step_index == len(visualizer.timeline) - 1
    visualizer._handle_keydown(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_HOME))
    assert visualizer.current_step_index == 0


def test_all_exact_results_render_a_final_badge() -> None:
    cases = (
        (None, ExactStatus.UNIQUE, "유일해"),
        (MULTIPLE_GRID, ExactStatus.MULTIPLE, "복수해"),
        (UNSOLVABLE_GRID, ExactStatus.UNSOLVABLE, "해 없음"),
    )

    for grid, status, badge in cases:
        puzzle = load_preset("쉬움") if grid is None else Puzzle.from_region_grid(grid)
        visualizer = MeowVisualizer(puzzle, solve(puzzle))
        visualizer.current_step_index = len(visualizer.timeline) - 1

        visualizer.draw()

        assert visualizer.result.exact_result.status is status
        assert badge in visualizer._status_badge()[0]


def test_escape_returns_the_region_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    puzzle = load_preset("쉬움")
    visualizer = MeowVisualizer(puzzle, solve(puzzle))
    monkeypatch.setattr(
        pygame.event,
        "wait",
        lambda *_args: pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE),
    )
    monkeypatch.setattr(pygame.event, "get", lambda: [])

    assert visualizer.run() == puzzle.region_grid

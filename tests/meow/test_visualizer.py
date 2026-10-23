from __future__ import annotations

import asyncio
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from meow.model import Puzzle
from meow.puzzle_catalog import load_preset
from meow.solver import solve
from meow.timeline import TimelineKind
from meow.visualizer import MeowVisualizer
from puzzle_common.ui_style import RED

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


def test_core_frames_render(stalled_probe_puzzle: Puzzle) -> None:
    puzzle = stalled_probe_puzzle
    visualizer = MeowVisualizer(puzzle, solve(puzzle))
    core_kinds = (
        TimelineKind.LOGIC_STEP,
        TimelineKind.PROBE_START,
        TimelineKind.PROBE_END,
        TimelineKind.RESTORE,
        TimelineKind.BACKTRACK_SEARCH,
        TimelineKind.FINAL,
    )

    for kind in core_kinds:
        visualizer.current_step_index = next(
            index
            for index, frame in enumerate(visualizer.timeline)
            if frame.kind is kind
        )
        visualizer.draw()
        if kind is TimelineKind.PROBE_START:
            assert visualizer.current_frame.active_assumption is not None
            assert visualizer._effect_groups() == ()

    visualizer.current_step_index = next(
        index
        for index, frame in enumerate(visualizer.timeline)
        if frame.kind is TimelineKind.LOGIC_STEP and frame.active_assumption is not None
    )
    visualizer.draw()
    details = visualizer._presentation()
    assert details.assumption.endswith(" = 고양이")
    assert details.annotations


def test_presentation_keeps_structured_effects_and_reason() -> None:
    puzzle = load_preset("쉬움")
    visualizer = MeowVisualizer(puzzle, solve(puzzle))
    visualizer.current_step_index = 1

    details = visualizer._presentation()

    assert details.title == "Basic Deductions"
    assert "R1C3" in details.reason
    assert details.effects == (("고양이 확정 · 1", ("R1C3 = 고양이",)),)
    assert details.region_colors


def test_all_exact_results_render_a_final_badge() -> None:
    cases = (
        (None, "유일해"),
        (MULTIPLE_GRID, "복수해"),
        (UNSOLVABLE_GRID, "해 없음"),
    )

    for grid, badge in cases:
        puzzle = load_preset("쉬움") if grid is None else Puzzle.from_region_grid(grid)
        visualizer = MeowVisualizer(puzzle, solve(puzzle))
        visualizer.current_step_index = len(visualizer.timeline) - 1

        visualizer.draw()

        assert badge in visualizer._status_badge()[0]


def test_new_exclusion_preserves_region_color_and_uses_red_x() -> None:
    puzzle = load_preset("쉬움")
    visualizer = MeowVisualizer(puzzle, solve(puzzle))
    visualizer.current_step_index = next(
        index
        for index, frame in enumerate(visualizer.timeline)
        if frame.logic_step is not None and frame.logic_step.deduction.exclusions
    )
    deduction = visualizer.current_frame.logic_step.deduction
    cell = deduction.exclusions[0]
    rect = visualizer._cell_rect(cell)

    visualizer.draw()

    background_point = (rect.centerx, rect.top + max(3, rect.height // 10))
    assert (
        tuple(visualizer.screen.get_at(background_point)[:3])
        == (visualizer.region_colors[puzzle.region_label(cell)])
    )

    padding = max(2, rect.width // 5)
    x_start = (rect.left + padding, rect.top + padding)
    assert tuple(visualizer.screen.get_at(x_start)[:3]) == RED


def test_related_region_chip_uses_the_board_region_color() -> None:
    puzzle = load_preset("쉬움")
    visualizer = MeowVisualizer(puzzle, solve(puzzle))
    visualizer.current_step_index = next(
        index for index, frame in enumerate(visualizer.timeline) if frame.region_indices
    )
    region_index = visualizer.current_frame.region_indices[0]
    expected = visualizer.region_colors[puzzle.region_labels[region_index]]

    x, y = 10, 10
    visualizer.screen.fill((255, 255, 255))
    visualizer._draw_region_chips(visualizer._presentation().region_colors, x, y)
    chip_y = y + 5
    label_width = visualizer.fonts.candidate.size("관련 색상 영역")[0]
    chip_size = max(16, visualizer.fonts.candidate.get_height() - 1)
    chip_center = (
        x + label_width + 10 + chip_size // 2,
        chip_y + chip_size // 2,
    )
    assert tuple(visualizer.screen.get_at(chip_center)[:3]) == expected


def test_escape_returns_the_region_grid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    puzzle = load_preset("쉬움")
    visualizer = MeowVisualizer(puzzle, solve(puzzle))

    async def advance_frame(clock: pygame.time.Clock) -> float:
        await asyncio.sleep(0)
        return 1 / 60

    monkeypatch.setattr(
        "puzzle_common.playback.next_frame",
        advance_frame,
    )
    monkeypatch.setattr(
        pygame.event,
        "get",
        lambda: [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE)],
    )

    assert asyncio.run(visualizer.run()) == puzzle.region_grid

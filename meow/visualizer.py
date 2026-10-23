"""Event-driven pygame playback for a precomputed MEOW Queens solve trace."""

from __future__ import annotations

import pygame

from puzzle_common.engine import SolveResult
from puzzle_common.playback import PlaybackDetails, PlaybackScreen
from puzzle_common.presentation import PlaybackFrame
from puzzle_common.ui_style import (
    ACCENT,
    GRAY,
    ORANGE,
    PRIMARY_DARK,
    RED,
    WHITE,
    Color,
)

from .model import Cell, Puzzle, RegionGrid
from .presentation import describe_frame
from .solve_types import Deduction
from .state import CellState, LogicSnapshot
from .ui_style import (
    draw_region_grid_lines,
    get_fonts,
    region_palette,
)


def _draw_cat(
    screen: pygame.Surface,
    rect: pygame.Rect,
    color: Color,
) -> None:
    """Draw a scalable cat face without depending on an external image asset."""

    size = min(rect.width, rect.height)
    center_x, center_y = rect.center
    if size < 18:
        radius = max(2, size // 4)
        pygame.draw.circle(screen, color, rect.center, radius)
        pygame.draw.polygon(
            screen,
            color,
            (
                (center_x - radius, center_y - radius // 2),
                (center_x - radius, center_y - radius * 2),
                (center_x, center_y - radius),
            ),
        )
        pygame.draw.polygon(
            screen,
            color,
            (
                (center_x + radius, center_y - radius // 2),
                (center_x + radius, center_y - radius * 2),
                (center_x, center_y - radius),
            ),
        )
        return

    radius = max(5, round(size * 0.27))
    head_y = center_y + round(size * 0.04)
    ear_height = max(4, round(size * 0.23))
    ear_spread = max(4, round(size * 0.2))
    pygame.draw.polygon(
        screen,
        color,
        (
            (center_x - radius + 2, head_y - radius // 2),
            (center_x - ear_spread, head_y - radius - ear_height),
            (center_x - 1, head_y - radius + 2),
        ),
    )
    pygame.draw.polygon(
        screen,
        color,
        (
            (center_x + radius - 2, head_y - radius // 2),
            (center_x + ear_spread, head_y - radius - ear_height),
            (center_x + 1, head_y - radius + 2),
        ),
    )
    pygame.draw.circle(screen, color, (center_x, head_y), radius)

    face = WHITE
    eye_y = head_y - radius // 5
    eye_offset = max(2, radius // 3)
    eye_radius = max(1, radius // 8)
    pygame.draw.circle(screen, face, (center_x - eye_offset, eye_y), eye_radius)
    pygame.draw.circle(screen, face, (center_x + eye_offset, eye_y), eye_radius)
    nose_y = head_y + radius // 5
    pygame.draw.polygon(
        screen,
        (244, 114, 182),
        (
            (center_x - 2, nose_y),
            (center_x + 2, nose_y),
            (center_x, nose_y + 3),
        ),
    )
    whisker_length = max(4, radius // 2)
    for offset in (-2, 2):
        y = nose_y + offset
        pygame.draw.line(
            screen,
            face,
            (center_x - 3, y),
            (center_x - 3 - whisker_length, y + offset // 2),
            1,
        )
        pygame.draw.line(
            screen,
            face,
            (center_x + 3, y),
            (center_x + 3 + whisker_length, y + offset // 2),
            1,
        )


def _draw_x(screen: pygame.Surface, rect: pygame.Rect, color: Color) -> None:
    padding = max(2, rect.width // 5)
    width = max(1, rect.width // 13)
    pygame.draw.line(
        screen,
        color,
        (rect.left + padding, rect.top + padding),
        (rect.right - padding, rect.bottom - padding),
        width,
    )
    pygame.draw.line(
        screen,
        color,
        (rect.right - padding, rect.top + padding),
        (rect.left + padding, rect.bottom - padding),
        width,
    )


class MeowVisualizer(PlaybackScreen[RegionGrid, LogicSnapshot, Deduction, Cell, str]):
    """Interpret MEOW trace frames and render its colored queen board."""

    def __init__(self, puzzle: Puzzle, result: SolveResult) -> None:
        if not isinstance(puzzle, Puzzle):
            raise TypeError("MeowVisualizer는 Puzzle을 받아야 합니다.")
        self.puzzle = puzzle
        self.region_colors = region_palette(puzzle.region_labels)
        super().__init__(
            result=result,
            edit_draft=puzzle.region_grid,
            board_size=puzzle.size,
            caption="MEOW · Queens 퍼즐 풀이 과정",
            fonts=get_fonts(),
        )

    def _validate_frames(self) -> None:
        if any(not isinstance(frame.snapshot, LogicSnapshot) for frame in self.frames):
            raise TypeError("MeowVisualizer는 MEOW 상태를 받아야 합니다.")
        if any(frame.snapshot.puzzle != self.puzzle for frame in self.frames):
            raise ValueError("풀이 결과가 전달된 문제에서 생성되지 않았습니다.")

    def _draw_board(self, frame: PlaybackFrame) -> None:
        self._draw_region_backgrounds()
        draw_region_grid_lines(
            self.screen,
            self.puzzle.region_grid,
            self.board_origin,
            self.cell_size,
            region_width=max(2, min(4, self.cell_size // 12)),
        )
        self._draw_cell_states(frame)
        if frame.active_assumption is not None:
            self._outline_cell(frame.active_assumption, ORANGE, 3)

    def _presentation(self, frame: PlaybackFrame) -> PlaybackDetails:
        return describe_frame(frame, self.result)

    def _draw_region_backgrounds(self) -> None:
        for cell in self.puzzle.cells:
            label = self.puzzle.region_label(cell)
            pygame.draw.rect(
                self.screen,
                self.region_colors[label],
                self.layout.cell_rect(cell),
            )

    def _draw_cell_states(self, frame: PlaybackFrame) -> None:
        new_cats: set[Cell] = set()
        new_exclusions: set[Cell] = set()
        if frame.deduction is not None:
            new_cats.update(frame.deduction.placements)
            new_exclusions.update(frame.deduction.exclusions)

        for cell in self.puzzle.cells:
            state = frame.snapshot.status_at(cell)
            rect = self.layout.cell_rect(cell)
            if state is CellState.EXCLUDED:
                _draw_x(self.screen, rect, RED if cell in new_exclusions else GRAY)
            elif state is CellState.CAT:
                color = (
                    ORANGE
                    if cell == frame.active_assumption
                    else ACCENT
                    if cell in new_cats
                    else PRIMARY_DARK
                )
                _draw_cat(self.screen, rect, color)

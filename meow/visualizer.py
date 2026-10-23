"""Event-driven pygame playback for a precomputed MEOW Queens solve trace."""

from __future__ import annotations

import pygame

from puzzle_common.coordinates import cell_name as _cell_name
from puzzle_common.playback import PlaybackDetails, PlaybackScreen
from puzzle_common.presentation import Outcome, PlaybackData
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
from .solve_types import SOLVER_ALGORITHM_LABELS, SolverAlgorithm
from .state import CellState
from .timeline import PlaybackFrame, TimelineKind
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


class MeowVisualizer(PlaybackScreen[RegionGrid, PlaybackFrame]):
    """Interpret MEOW trace frames and render its colored queen board."""

    def __init__(self, puzzle: Puzzle, data: PlaybackData[PlaybackFrame]) -> None:
        if not isinstance(puzzle, Puzzle):
            raise TypeError("MeowVisualizer는 Puzzle을 받아야 합니다.")
        if not isinstance(data, PlaybackData) or any(
            not isinstance(frame, PlaybackFrame) for frame in data.frames
        ):
            raise TypeError(
                "MeowVisualizer는 PlaybackData[PlaybackFrame]을 받아야 합니다."
            )
        if any(
            frame.snapshot.puzzle.region_grid != puzzle.region_grid
            for frame in data.frames
        ):
            raise ValueError("풀이 결과가 전달된 문제에서 생성되지 않았습니다.")

        self.puzzle = puzzle
        self.region_colors = region_palette(puzzle.region_labels)
        super().__init__(
            data=data,
            edit_draft=puzzle.region_grid,
            board_size=puzzle.size,
            caption="MEOW · Queens 퍼즐 풀이 과정",
            fonts=get_fonts(),
        )

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
        probing = (
            frame.kind is TimelineKind.LOGIC_STEP
            and frame.active_assumption is not None
        )
        return PlaybackDetails(
            title=frame.title,
            reason=frame.message or frame.title,
            effects=self._effect_groups(frame),
            annotations=(
                (SOLVER_ALGORITHM_LABELS[SolverAlgorithm.SINGLETON_PROBING], ORANGE),
            )
            if probing
            else (),
            assumption=f"{_cell_name(frame.active_assumption)} = 고양이"
            if frame.active_assumption is not None
            else "",
            region_colors=self._region_chip_colors(frame),
        )

    def _draw_region_backgrounds(self) -> None:
        for cell in self.puzzle.cells:
            label = self.puzzle.region_label(cell)
            pygame.draw.rect(
                self.screen,
                self.region_colors[label],
                self._cell_rect(cell),
            )

    def _draw_cell_states(self, frame: PlaybackFrame) -> None:
        new_cats: set[Cell] = set()
        new_exclusions: set[Cell] = set()
        if frame.logic_step is not None:
            new_cats.update(frame.logic_step.deduction.placements)
            new_exclusions.update(frame.logic_step.deduction.exclusions)

        for cell in self.puzzle.cells:
            state = frame.snapshot.status_at(cell)
            rect = self._cell_rect(cell)
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

    def _region_chip_colors(self, frame: PlaybackFrame) -> tuple[Color, ...]:
        return tuple(
            self.region_colors[self.puzzle.region_labels[index]]
            for index in frame.region_indices
        )

    def _effect_groups(
        self, frame: PlaybackFrame
    ) -> tuple[tuple[str, tuple[str, ...]], ...]:
        if frame.logic_step is not None:
            deduction = frame.logic_step.deduction
            groups: list[tuple[str, tuple[str, ...]]] = []
            for label, value, cells in (
                ("고양이 확정", "고양이", deduction.placements),
                ("X 기입", "X", deduction.exclusions),
            ):
                if cells:
                    groups.append(
                        (
                            f"{label} · {len(cells)}",
                            tuple(f"{_cell_name(cell)} = {value}" for cell in cells),
                        )
                    )
            return tuple(groups)

        if frame.kind is TimelineKind.RESTORE and frame.focus_cells:
            return (
                (
                    "가정 제거 · 1",
                    (f"{_cell_name(frame.focus_cells[0])} 원래 상태로 복원",),
                ),
            )
        if frame.kind is TimelineKind.BACKTRACK_SEARCH:
            search_label = SOLVER_ALGORITHM_LABELS[SolverAlgorithm.BACKTRACK_SEARCH]
            return (("전환", (f"{search_label}으로 답 하나 찾기",)),)
        if frame.kind is TimelineKind.FINAL:
            if self.outcome is Outcome.UNSOLVABLE:
                return (("최종 판정", ("가능한 고양이 배치 없음",)),)
            qualifier = "대표 해" if self.outcome is Outcome.MULTIPLE else "유일해"
            return (
                (
                    "최종 배치",
                    (f"고양이 {len(frame.snapshot.cats)}마리 · {qualifier}",),
                ),
            )
        return ()

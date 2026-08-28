"""Event-driven pygame playback for a precomputed MEOW Queens solve trace."""

from __future__ import annotations

from collections.abc import Iterable

import pygame

from .exact_solver import ExactStatus
from .model import Cell, Puzzle, RegionGrid
from .runtime import next_frame
from .solve_types import SOLVER_ALGORITHM_LABELS, SolverAlgorithm
from .solver import SolveResult
from .state import CellState
from .timeline import PlaybackFrame, TimelineKind, build_timeline
from .ui_components import Button
from .ui_style import (
    ACCENT,
    ACCENT_LIGHT,
    APP_BACKGROUND,
    BLACK,
    BORDER,
    GRAY,
    LIGHT_GRAY,
    ORANGE,
    ORANGE_LIGHT,
    PRIMARY,
    PRIMARY_DARK,
    RED,
    RED_LIGHT,
    WHITE,
    Color,
    configure_display,
    draw_region_grid_lines,
    get_fonts,
    region_palette,
    wrap_text,
)

_NAVIGATION_REPEAT_DELAY = 0.36
_NAVIGATION_REPEAT_INTERVAL = 0.08
_AUTOPLAY_INTERVAL = 0.9
_TARGET_BOARD_SIZE = 620
_MAX_CELL_SIZE = 96
_MIN_CELL_SIZE = 8
_MARGIN = 44
_PANEL_GAP = 26
_PANEL_WIDTH = 350
_MIN_WINDOW_HEIGHT = 700

type _NavigationSource = tuple[str, int]


def _cell_name(cell: Cell) -> str:
    row, column = cell
    return f"R{row + 1}C{column + 1}"


def _pack_effect_items(
    items: tuple[str, ...],
    font: pygame.font.Font,
    max_width: int,
) -> tuple[str, ...]:
    """Pack complete cell effects onto lines without splitting coordinates."""

    if not items:
        return ()
    separator = "   "
    lines: list[str] = []
    current = items[0]
    for item in items[1:]:
        candidate = f"{current}{separator}{item}"
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = item
    lines.append(current)
    return tuple(lines)


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


class MeowVisualizer:
    """Navigate immutable playback frames without rerunning the solver."""

    def __init__(self, puzzle: Puzzle, result: SolveResult) -> None:
        if not isinstance(puzzle, Puzzle):
            raise TypeError("MeowVisualizer는 Puzzle을 받아야 합니다.")
        if not isinstance(result, SolveResult):
            raise TypeError("MeowVisualizer는 SolveResult를 받아야 합니다.")
        source = result.initial_logic_result.initial_state.puzzle
        if source.region_grid != puzzle.region_grid:
            raise ValueError("풀이 결과가 전달된 문제에서 생성되지 않았습니다.")

        self.puzzle = puzzle
        self.result = result
        self.timeline = build_timeline(result)
        self.current_step_index = 0
        self.running = True
        self.autoplay_enabled = False
        self.autoplay_timer = 0.0
        self._held_navigation_sources: dict[_NavigationSource, int] = {}
        self._active_navigation_source: _NavigationSource | None = None
        self._navigation_repeat_timer = 0.0
        self._navigation_repeat_started = False

        self.cell_size = max(
            _MIN_CELL_SIZE,
            min(_MAX_CELL_SIZE, _TARGET_BOARD_SIZE // puzzle.size),
        )
        self.margin = _MARGIN
        self.board_size = puzzle.size * self.cell_size
        self.board_origin = (self.margin, self.margin)
        width = self.margin + self.board_size + _PANEL_GAP + _PANEL_WIDTH + self.margin
        self.height = max(self.board_size + self.margin * 2, _MIN_WINDOW_HEIGHT)
        self.panel_rect = pygame.Rect(
            self.margin + self.board_size + _PANEL_GAP,
            self.margin,
            _PANEL_WIDTH,
            self.height - self.margin * 2,
        )
        self.screen = configure_display(
            (width, self.height),
            "MEOW · Queens 퍼즐 풀이 과정",
        )
        self.fonts = get_fonts()
        self.region_colors = region_palette(puzzle.region_labels)
        self._init_buttons()

    @property
    def current_frame(self) -> PlaybackFrame:
        return self.timeline[self.current_step_index]

    def _init_buttons(self) -> None:
        inner_x = self.panel_rect.left + 16
        gap = 8
        inner_width = self.panel_rect.width - 32
        third = (inner_width - gap * 2) // 3
        controls_y = self.panel_rect.bottom - 112
        self.previous_button = Button(
            pygame.Rect(inner_x, controls_y, third, 38),
            "이전",
            PRIMARY,
            self.fonts.button,
        )
        self.play_button = Button(
            pygame.Rect(inner_x + third + gap, controls_y, third, 38),
            "재생",
            ACCENT,
            self.fonts.button,
        )
        self.next_button = Button(
            pygame.Rect(inner_x + (third + gap) * 2, controls_y, third, 38),
            "다음",
            PRIMARY,
            self.fonts.button,
        )
        self.edit_button = Button(
            pygame.Rect(inner_x, controls_y + 50, inner_width, 38),
            "문제 입력으로 돌아가기",
            PRIMARY_DARK,
            self.fonts.button,
        )

    def _cell_rect(self, cell: Cell) -> pygame.Rect:
        row, column = cell
        return pygame.Rect(
            self.board_origin[0] + column * self.cell_size,
            self.board_origin[1] + row * self.cell_size,
            self.cell_size,
            self.cell_size,
        )

    def _outline_cell(self, cell: Cell, color: Color, width: int = 3) -> None:
        rect = self._cell_rect(cell).inflate(-4, -4)
        if rect.width <= 0 or rect.height <= 0:
            return
        pygame.draw.rect(
            self.screen,
            color,
            rect,
            width=max(1, min(width, rect.width // 2)),
            border_radius=max(0, min(5, rect.width // 5)),
        )

    def draw(self) -> None:
        self.screen.fill(APP_BACKGROUND)
        board_rect = pygame.Rect(
            *self.board_origin,
            self.board_size,
            self.board_size,
        )
        pygame.draw.rect(
            self.screen,
            LIGHT_GRAY,
            board_rect.move(0, 4),
            border_radius=5,
        )
        self._draw_region_backgrounds()
        draw_region_grid_lines(
            self.screen,
            self.puzzle.region_grid,
            self.board_origin,
            self.cell_size,
            region_width=max(2, min(4, self.cell_size // 12)),
        )
        self._draw_coordinates()
        self._draw_cell_states()
        if self.current_frame.active_assumption is not None:
            self._outline_cell(self.current_frame.active_assumption, ORANGE, 3)
        self._draw_panel()
        pygame.display.flip()

    def _draw_region_backgrounds(self) -> None:
        for cell in self.puzzle.cells:
            label = self.puzzle.region_label(cell)
            pygame.draw.rect(
                self.screen,
                self.region_colors[label],
                self._cell_rect(cell),
            )

    def _draw_coordinates(self) -> None:
        if self.cell_size < 18:
            return
        font = self.fonts.candidate
        start_x, start_y = self.board_origin
        for index in range(self.puzzle.size):
            column_label = font.render(f"C{index + 1}", True, GRAY)
            row_label = font.render(f"R{index + 1}", True, GRAY)
            column_center = start_x + index * self.cell_size + self.cell_size // 2
            row_center = start_y + index * self.cell_size + self.cell_size // 2
            self.screen.blit(
                column_label,
                column_label.get_rect(center=(column_center, start_y - 13)),
            )
            self.screen.blit(
                row_label,
                row_label.get_rect(center=(start_x - 17, row_center)),
            )

    def _draw_cell_states(self) -> None:
        frame = self.current_frame
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

    def _status_badge(self) -> tuple[str, Color, Color]:
        status = self.result.exact_result.status
        if status is ExactStatus.MULTIPLE:
            return "복수해 · 가능한 해 중 하나 표시", ORANGE, ORANGE_LIGHT
        if status is ExactStatus.UNSOLVABLE:
            return "해 없음 · 유효한 배치 없음", RED, RED_LIGHT
        return "유일해", ACCENT, ACCENT_LIGHT

    def _region_chip_colors(self) -> tuple[Color, ...]:
        return tuple(
            self.region_colors[self.puzzle.region_labels[index]]
            for index in self.current_frame.region_indices
        )

    def _draw_region_chips(self, x: int, y: int) -> int:
        colors = self._region_chip_colors()
        if not colors:
            return y

        y += 5
        label = self.fonts.candidate.render("관련 색상 영역", True, GRAY)
        self.screen.blit(label, (x, y + 1))
        chip_x = x + label.get_width() + 10
        chip_size = max(16, self.fonts.candidate.get_height() - 1)
        for color in colors:
            rect = pygame.Rect(chip_x, y, chip_size, chip_size)
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(
                self.screen,
                BLACK,
                rect,
                width=2,
                border_radius=4,
            )
            chip_x += chip_size + 6
        return y + max(label.get_height(), chip_size) + 8

    def _draw_panel(self) -> None:
        pygame.draw.rect(
            self.screen,
            LIGHT_GRAY,
            self.panel_rect.move(0, 4),
            border_radius=14,
        )
        pygame.draw.rect(self.screen, WHITE, self.panel_rect, border_radius=14)
        pygame.draw.rect(
            self.screen,
            BORDER,
            self.panel_rect,
            width=1,
            border_radius=14,
        )

        x = self.panel_rect.left + 18
        inner_width = self.panel_rect.width - 36
        y = self.panel_rect.top + 18
        self.screen.blit(
            self.fonts.title.render("MEOW · Queens 풀이 과정", True, PRIMARY_DARK),
            (x, y),
        )
        y += 38

        badge_text, badge_color, badge_background = self._status_badge()
        badge_surface = self.fonts.body.render(badge_text, True, badge_color)
        badge_rect = badge_surface.get_rect(topleft=(x + 9, y + 5)).inflate(18, 10)
        pygame.draw.rect(
            self.screen,
            badge_background,
            badge_rect,
            border_radius=8,
        )
        self.screen.blit(badge_surface, (badge_rect.left + 9, badge_rect.top + 5))
        y = badge_rect.bottom + 16

        counter = f"{self.current_step_index + 1} / {len(self.timeline)} 단계"
        self.screen.blit(self.fonts.heading.render(counter, True, BLACK), (x, y))
        y += 30
        y = self._draw_wrapped(
            self.current_frame.title,
            x,
            y,
            color=PRIMARY,
            font=self.fonts.heading,
            max_width=inner_width,
            max_y=y + 50,
        )

        if (
            self.current_frame.kind is TimelineKind.LOGIC_STEP
            and self.current_frame.active_assumption is not None
        ):
            self.screen.blit(
                self.fonts.body.render(
                    SOLVER_ALGORITHM_LABELS[SolverAlgorithm.SINGLETON_PROBING],
                    True,
                    ORANGE,
                ),
                (x, y + 3),
            )
            y += 25

        y = self._draw_region_chips(x, y)

        pygame.draw.line(
            self.screen,
            LIGHT_GRAY,
            (x, y + 4),
            (self.panel_rect.right - 18, y + 4),
            width=1,
        )
        y += 18
        panel_content_bottom = self.previous_button.rect.top - 42
        assumption_space = (
            64 if self.current_frame.active_assumption is not None else 0
        )
        details_bottom = panel_content_bottom - assumption_space

        self.screen.blit(self.fonts.body.render("사유", True, PRIMARY), (x, y))
        y += 23
        y = self._draw_wrapped(
            self.current_frame.message or self.current_frame.title,
            x,
            y,
            color=GRAY,
            max_width=inner_width,
            max_y=details_bottom,
        )

        effect_groups = self._effect_groups()
        if effect_groups and y + 30 <= details_bottom:
            y += 9
            self.screen.blit(
                self.fonts.body.render("적용 내역", True, PRIMARY),
                (x, y),
            )
            y += 23
            for label, items in effect_groups:
                if self.current_frame.logic_step is None:
                    if y + 21 > details_bottom:
                        break
                    self.screen.blit(
                        self.fonts.candidate.render(label, True, BLACK),
                        (x, y),
                    )
                    y += 19
                y = self._draw_effect_items(
                    items,
                    x,
                    y,
                    max_width=inner_width,
                    max_y=details_bottom,
                )
                y += 5

        if self.current_frame.active_assumption is not None:
            assumption = _cell_name(self.current_frame.active_assumption)
            y += 8
            self.screen.blit(
                self.fonts.body.render("활성 가정", True, ORANGE),
                (x, y),
            )
            y += 22
            self.screen.blit(
                self.fonts.body.render(f"{assumption} = 고양이", True, GRAY),
                (x, y),
            )

        mouse_pos = pygame.mouse.get_pos()
        self.play_button.text = "일시정지" if self.autoplay_enabled else "재생"
        for button in (
            self.previous_button,
            self.play_button,
            self.next_button,
            self.edit_button,
        ):
            button.update_hover(mouse_pos)
            button.draw(self.screen)

        help_text = "←/→ 이동 · Home/End · Space 재생 · Esc 편집"
        help_surface = self.fonts.candidate.render(help_text, True, GRAY)
        self.screen.blit(
            help_surface,
            help_surface.get_rect(
                center=(self.panel_rect.centerx, self.previous_button.rect.top - 17)
            ),
        )

    def _draw_wrapped(
        self,
        text: str,
        x: int,
        y: int,
        *,
        color: Color,
        max_width: int,
        max_y: int,
        font: pygame.font.Font | None = None,
    ) -> int:
        selected_font = font or self.fonts.body
        line_height = selected_font.get_linesize() + 2
        lines = wrap_text(text, selected_font, max_width)
        available_lines = max(0, (max_y - y) // line_height)
        if len(lines) > available_lines:
            if available_lines == 0:
                return y
            lines = (*lines[: available_lines - 1], "…")
        for line in lines:
            self.screen.blit(selected_font.render(line, True, color), (x, y))
            y += line_height
        return y

    def _draw_effect_items(
        self,
        items: tuple[str, ...],
        x: int,
        y: int,
        *,
        max_width: int,
        max_y: int,
    ) -> int:
        lines = _pack_effect_items(items, self.fonts.body, max_width)
        line_height = self.fonts.body.get_linesize() + 2
        available_lines = max(0, (max_y - y) // line_height)
        if len(lines) > available_lines:
            if available_lines == 0:
                return y
            shown_count = available_lines - 1
            remaining = len(lines) - shown_count
            lines = (*lines[:shown_count], f"… 외 {remaining}줄")
        for line in lines:
            self.screen.blit(self.fonts.body.render(line, True, GRAY), (x, y))
            y += line_height
        return y

    def _effect_groups(self) -> tuple[tuple[str, tuple[str, ...]], ...]:
        frame = self.current_frame
        if frame.logic_step is not None:
            deduction = frame.logic_step.deduction
            groups: list[tuple[str, tuple[str, ...]]] = []
            if deduction.placements:
                groups.append(
                    (
                        f"고양이 확정 · {len(deduction.placements)}",
                        tuple(
                            f"{_cell_name(cell)} = 고양이"
                            for cell in deduction.placements
                        ),
                    )
                )
            if deduction.exclusions:
                groups.append(
                    (
                        f"X 기입 · {len(deduction.exclusions)}",
                        tuple(
                            f"{_cell_name(cell)} = X" for cell in deduction.exclusions
                        ),
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
            status = self.result.exact_result.status
            if status is ExactStatus.UNSOLVABLE:
                return (("최종 판정", ("가능한 고양이 배치 없음",)),)
            qualifier = "대표 해" if status is ExactStatus.MULTIPLE else "유일해"
            return (
                (
                    "최종 배치",
                    (f"고양이 {len(frame.snapshot.cats)}마리 · {qualifier}",),
                ),
            )
        return ()

    def _navigate(self, offset: int) -> bool:
        target = max(
            0,
            min(len(self.timeline) - 1, self.current_step_index + offset),
        )
        if target == self.current_step_index:
            return False
        self.current_step_index = target
        self.autoplay_timer = 0.0
        return True

    def _set_index(self, index: int) -> None:
        self.current_step_index = max(0, min(len(self.timeline) - 1, index))
        self.autoplay_timer = 0.0

    def _toggle_autoplay(self) -> None:
        self._clear_navigation_holds()
        if self.current_step_index == len(self.timeline) - 1:
            self.current_step_index = 0
        self.autoplay_enabled = not self.autoplay_enabled
        self.autoplay_timer = 0.0

    def _begin_navigation_hold(
        self,
        source: _NavigationSource,
        offset: int,
    ) -> None:
        if source in self._held_navigation_sources:
            return
        self.autoplay_enabled = False
        self._held_navigation_sources[source] = offset
        self._active_navigation_source = source
        self._navigation_repeat_timer = 0.0
        self._navigation_repeat_started = False
        self._navigate(offset)

    def _end_navigation_hold(self, source: _NavigationSource) -> None:
        if source not in self._held_navigation_sources:
            return
        del self._held_navigation_sources[source]
        if self._active_navigation_source != source:
            return
        self._active_navigation_source = (
            next(reversed(self._held_navigation_sources), None)
            if self._held_navigation_sources
            else None
        )
        self._navigation_repeat_timer = 0.0
        self._navigation_repeat_started = False

    def _clear_navigation_holds(self) -> None:
        self._held_navigation_sources.clear()
        self._active_navigation_source = None
        self._navigation_repeat_timer = 0.0
        self._navigation_repeat_started = False

    def _update_navigation_hold(self, elapsed: float) -> bool:
        source = self._active_navigation_source
        if source is None:
            return False
        offset = self._held_navigation_sources.get(source)
        if offset is None:
            self._clear_navigation_holds()
            return False

        changed = False
        self._navigation_repeat_timer += elapsed
        threshold = (
            _NAVIGATION_REPEAT_INTERVAL
            if self._navigation_repeat_started
            else _NAVIGATION_REPEAT_DELAY
        )
        while self._navigation_repeat_timer >= threshold:
            self._navigation_repeat_timer -= threshold
            self._navigation_repeat_started = True
            changed = self._navigate(offset) or changed
            threshold = _NAVIGATION_REPEAT_INTERVAL
        return changed

    def _update_autoplay(self, elapsed: float) -> bool:
        if not self.autoplay_enabled:
            return False
        self.autoplay_timer += elapsed
        if self.autoplay_timer < _AUTOPLAY_INTERVAL:
            return False
        self.autoplay_timer = 0.0
        changed = self._navigate(1)
        if not changed:
            self.autoplay_enabled = False
        return changed

    def _handle_keydown(self, event: pygame.event.Event) -> str | None:
        if event.key == pygame.K_ESCAPE:
            return "edit"
        if event.key == pygame.K_LEFT:
            self._begin_navigation_hold(("key", event.key), -1)
        elif event.key == pygame.K_RIGHT:
            self._begin_navigation_hold(("key", event.key), 1)
        elif event.key == pygame.K_HOME:
            self.autoplay_enabled = False
            self._set_index(0)
        elif event.key == pygame.K_END:
            self.autoplay_enabled = False
            self._set_index(len(self.timeline) - 1)
        elif event.key == pygame.K_SPACE:
            self._toggle_autoplay()
        return None

    def _handle_mouse_down(self, event: pygame.event.Event) -> str | None:
        if event.button != 1:
            return None
        if self.previous_button.is_clicked(event.pos):
            self._begin_navigation_hold(("mouse", event.button), -1)
        elif self.play_button.is_clicked(event.pos):
            self._toggle_autoplay()
        elif self.next_button.is_clicked(event.pos):
            self._begin_navigation_hold(("mouse", event.button), 1)
        elif self.edit_button.is_clicked(event.pos):
            return "edit"
        return None

    def _handle_events(
        self,
        events: Iterable[pygame.event.Event],
    ) -> str | None:
        for event in events:
            if event.type == pygame.QUIT:
                self._clear_navigation_holds()
                self.running = False
                return None
            if event.type == pygame.WINDOWFOCUSLOST:
                self._clear_navigation_holds()
            elif event.type == pygame.KEYDOWN:
                action = self._handle_keydown(event)
                if action is not None:
                    return action
            elif event.type == pygame.KEYUP and event.key in (
                pygame.K_LEFT,
                pygame.K_RIGHT,
            ):
                self._end_navigation_hold(("key", event.key))
            elif event.type == pygame.MOUSEBUTTONDOWN:
                action = self._handle_mouse_down(event)
                if action is not None:
                    return action
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._end_navigation_hold(("mouse", event.button))
        return None

    async def run(self) -> RegionGrid | None:
        """Run until the user requests editing or closes the application."""

        clock = pygame.time.Clock()
        self.draw()
        while self.running:
            elapsed = await next_frame(clock)
            timers_were_active = (
                self.autoplay_enabled or self._active_navigation_source is not None
            )
            events = pygame.event.get()

            action = self._handle_events(events)
            if action == "edit":
                return self.puzzle.region_grid
            if not self.running:
                break

            changed = bool(events)
            if timers_were_active:
                changed = self._update_navigation_hold(elapsed) or changed
                changed = self._update_autoplay(elapsed) or changed
            if changed:
                self.draw()
        return None

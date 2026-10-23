"""미리 계산된 구조화된 풀이 기록의 읽기 전용 pygame 화면."""

from collections.abc import Iterable

import pygame

from .board import Grid, Puzzle
from .runtime import next_frame
from .solve_types import (
    SolveResult,
    SolveStatus,
    SolveStep,
    StepKind,
    Technique,
    TechniqueResult,
)
from .topology import SIZE, UNITS, Cell
from .ui_components import Button
from .ui_style import (
    ACCENT,
    ACCENT_YELLOW,
    BLACK,
    CANDIDATE_GRAY,
    GRAY,
    LIGHT_GRAY,
    ORANGE,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_LIGHT,
    RED,
    WHITE,
    configure_display,
    draw_sudoku_grid_lines,
    get_fonts,
    wrap_text,
)

_STEP_LABELS: dict[StepKind, str] = {
    StepKind.INITIAL_STATE: "초기 상태",
    StepKind.TECHNIQUE: "논리 기법",
    StepKind.ASSUMPTION: "한 단계 가정",
    StepKind.ASSUMPTION_STALLED: "가정 정체",
    StepKind.ASSUMPTION_SOLVED: "가정에서 해 발견",
    StepKind.CONTRADICTION: "모순",
    StepKind.REFUTATION: "귀류 결론",
    StepKind.SEARCH_FALLBACK: "백트래킹 전환",
    StepKind.SOLVED: "풀이 완료",
    StepKind.UNSOLVABLE: "해 없음",
}

_TECHNIQUE_LABELS: dict[Technique, str] = {
    Technique.FULL_HOUSE: "Full House",
    Technique.NAKED_SINGLE: "Naked Single",
    Technique.HIDDEN_SINGLE: "Hidden Single",
    Technique.LOCKED_PAIR: "Locked Pair",
    Technique.NAKED_PAIR: "Naked Pair",
    Technique.LOCKED_CANDIDATES_POINTING: "Locked Candidates — Pointing",
    Technique.LOCKED_CANDIDATES_CLAIMING: "Locked Candidates — Claiming",
    Technique.LOCKED_TRIPLE: "Locked Triple",
    Technique.NAKED_TRIPLE: "Naked Triple",
    Technique.HIDDEN_PAIR: "Hidden Pair",
    Technique.HIDDEN_TRIPLE: "Hidden Triple",
    Technique.REFUTATION: "귀류법",
}

# 운영체제 키 반복 대신 프레임 시간으로 이동을 반복한다. 초기 지연으로
# 한 번의 클릭이나 키 입력이 여러 단계를 넘기지 않도록 한다.
_NAVIGATION_REPEAT_DELAY = 0.36
_NAVIGATION_REPEAT_INTERVAL = 0.08
_CELL_SIZE = 60
_MARGIN = 50
_PANEL_WIDTH = 300
_PANEL_X_OFFSET = 10
_AUTOPLAY_INTERVAL = 0.9

type _NavigationSource = tuple[str, int]


def _cell_name(cell: Cell) -> str:
    row, col = cell
    return f"R{row + 1}C{col + 1}"


def _deduction_effect_groups(
    deduction: TechniqueResult,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """구조화된 추론 데이터에서 라벨이 붙은 원자적 효과 항목을 반환한다."""

    groups: list[tuple[str, tuple[str, ...]]] = []
    if deduction.assignments:
        items = tuple(
            dict.fromkeys(
                f"{_cell_name(item.cell)} = {item.value}"
                for item in deduction.assignments
            )
        )
        groups.append((f"확정 칸 · {len(items)}", items))
    if deduction.eliminations:
        items = tuple(
            dict.fromkeys(
                f"{_cell_name(item.cell)}: {', '.join(map(str, sorted(item.values)))}"
                for item in deduction.eliminations
            )
        )
        groups.append((f"후보 제거 · {len(items)}", items))
    return tuple(groups)


def _pack_effect_items(
    items: tuple[str, ...],
    font: pygame.font.Font,
    max_width: int,
) -> tuple[str, ...]:
    """칸/값 쌍을 나누지 않고 효과 항목 전체를 줄에 배치한다."""

    if max_width <= 0:
        raise ValueError("텍스트 너비는 양수여야 합니다.")
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


def _deduction_reason(step: SolveStep) -> str:
    """생성자가 제공한 이유 문장을 반환하며 효과는 구조화된 필드로 관리한다."""

    deduction = step.deduction
    if deduction is None:
        return step.message
    return deduction.explanation or step.message


def _technique_label(step: SolveStep) -> str:
    """마지막 Full House 예외를 포함한 기법 라벨을 반환한다."""

    deduction = step.deduction
    if deduction is None:
        raise ValueError("논리 기법 라벨에는 deduction이 필요합니다.")
    if (
        deduction.technique is Technique.FULL_HOUSE
        and len(deduction.assignments) == 1
        and all(value != 0 for row in step.grid for value in row)
    ):
        return "Last Digit"
    return _TECHNIQUE_LABELS[deduction.technique]


class SudokuVisualizer:
    """솔버를 소유하거나 다시 실행하지 않고 불변 풀이 단계를 이동한다."""

    def __init__(
        self,
        puzzle: Puzzle,
        result: SolveResult,
    ) -> None:
        if not isinstance(puzzle, Puzzle):
            raise TypeError("SudokuVisualizer는 Puzzle을 받아야 합니다.")
        if not isinstance(result, SolveResult):
            raise TypeError("SudokuVisualizer는 SolveResult를 받아야 합니다.")
        if result.status is SolveStatus.UNSOLVABLE:
            raise ValueError("해가 있는 결과만 시각화할 수 있습니다.")
        if result.steps[0].grid != puzzle.grid:
            raise ValueError("풀이 결과가 전달된 문제에서 생성되지 않았습니다.")

        self.puzzle = puzzle
        self.result = result
        self.current_step_index = 0
        self.running = True
        self.autoplay_enabled = False
        self.autoplay_timer = 0.0
        self._held_navigation_sources: dict[_NavigationSource, int] = {}
        self._active_navigation_source: _NavigationSource | None = None
        self._navigation_repeat_timer = 0.0
        self._navigation_repeat_started = False

        self.cell_size = _CELL_SIZE
        self.margin = _MARGIN
        self.grid_width = SIZE * self.cell_size
        self.panel_width = _PANEL_WIDTH
        width = self.grid_width + 2 * self.margin + self.panel_width
        self.height = self.grid_width + 2 * self.margin
        self.screen = configure_display((width, self.height), "스도쿠 풀이 과정")
        self.fonts = get_fonts()
        self._init_buttons()

    @property
    def current_step(self) -> SolveStep:
        return self.result.steps[self.current_step_index]

    def _init_buttons(self) -> None:
        panel_x = self.margin + self.grid_width + _PANEL_X_OFFSET
        inner_x = panel_x + 12
        gap = 8
        inner_width = self.panel_width - _PANEL_X_OFFSET - 24
        third = (inner_width - gap * 2) // 3
        controls_y = self.height - 172
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
            "입력 화면으로 돌아가기",
            PRIMARY_DARK,
            self.fonts.button,
        )

    def draw(self) -> None:
        self.screen.fill(WHITE)
        self._draw_cell_highlights()
        draw_sudoku_grid_lines(
            self.screen,
            (self.margin, self.margin),
            self.cell_size,
        )
        self._draw_values_and_candidates()
        self._draw_panel()
        pygame.display.flip()

    def _draw_cell_highlights(self) -> None:
        step = self.current_step
        deduction = step.deduction
        context = set(deduction.context_cells if deduction else ())
        evidence = set(deduction.evidence_cells if deduction else ())
        eliminated = (
            {item.cell for item in deduction.eliminations} if deduction else set()
        )
        assigned = {item.cell for item in deduction.assignments} if deduction else set()
        contradiction = step.contradiction
        contradiction_context = (
            set(UNITS[contradiction.unit_index])
            if contradiction is not None and contradiction.unit_index is not None
            else set()
        )
        contradiction_cells = set(contradiction.cells if contradiction else ())

        for cell in context:
            self._fill_cell(cell, (*PRIMARY_LIGHT, 42))
        for cell in contradiction_context:
            self._fill_cell(cell, (*RED, 35))
        for cell in evidence:
            self._fill_cell(cell, (*ACCENT_YELLOW, 70))
        for cell in eliminated:
            self._fill_cell(cell, (*RED, 65))
        for cell in assigned:
            self._fill_cell(cell, (*ACCENT, 70))
        for cell in contradiction_cells:
            self._fill_cell(cell, (*RED, 80))

        if step.assumption is not None:
            decision_color = RED if step.kind is StepKind.REFUTATION else ORANGE
            self._fill_cell(step.assumption.cell, (*decision_color, 80))
            if step.depth:
                self._outline_cell(step.assumption.cell, ORANGE, width=3)

    def _fill_cell(self, cell: Cell, color: tuple[int, int, int, int]) -> None:
        row, col = cell
        rect = pygame.Rect(
            self.margin + col * self.cell_size + 2,
            self.margin + row * self.cell_size + 2,
            self.cell_size - 4,
            self.cell_size - 4,
        )
        surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        surface.fill(color)
        self.screen.blit(surface, rect.topleft)

    def _outline_cell(
        self, cell: Cell, color: tuple[int, int, int], *, width: int
    ) -> None:
        row, col = cell
        rect = pygame.Rect(
            self.margin + col * self.cell_size + 4,
            self.margin + row * self.cell_size + 4,
            self.cell_size - 8,
            self.cell_size - 8,
        )
        pygame.draw.rect(self.screen, color, rect, width=width, border_radius=4)

    def _draw_values_and_candidates(self) -> None:
        step = self.current_step
        assumption_cells = (
            {step.assumption.cell}
            if step.depth and step.assumption is not None
            else set()
        )
        removed_by_cell = {
            elimination.cell: elimination.values
            for elimination in (step.deduction.eliminations if step.deduction else ())
        }

        for row in range(SIZE):
            for col in range(SIZE):
                value = step.grid[row][col]
                center = (
                    self.margin + col * self.cell_size + self.cell_size // 2,
                    self.margin + row * self.cell_size + self.cell_size // 2,
                )
                if value:
                    if (row, col) in self.puzzle.givens:
                        color = BLACK
                    elif (row, col) in assumption_cells:
                        color = ORANGE
                    else:
                        color = PRIMARY_DARK
                    rendered = self.fonts.number.render(str(value), True, color)
                    self.screen.blit(rendered, rendered.get_rect(center=center))
                    continue

                candidates = step.candidates[row][col]
                removed = removed_by_cell.get((row, col), frozenset())
                self._draw_candidate_marks(row, col, candidates, removed)

    def _draw_candidate_marks(
        self,
        row: int,
        col: int,
        candidates: frozenset[int],
        removed: frozenset[int],
    ) -> None:
        for value in range(1, SIZE + 1):
            if value not in candidates and value not in removed:
                continue
            mark_row, mark_col = divmod(value - 1, 3)
            center = (
                self.margin
                + col * self.cell_size
                + (mark_col * 2 + 1) * self.cell_size // 6,
                self.margin
                + row * self.cell_size
                + (mark_row * 2 + 1) * self.cell_size // 6,
            )
            color = RED if value in removed else CANDIDATE_GRAY
            rendered = self.fonts.candidate.render(str(value), True, color)
            self.screen.blit(rendered, rendered.get_rect(center=center))
            if value in removed:
                y = center[1]
                pygame.draw.line(
                    self.screen,
                    RED,
                    (center[0] - 5, y),
                    (center[0] + 5, y),
                    width=1,
                )

    def _draw_panel(self) -> None:
        panel_x = self.margin + self.grid_width + _PANEL_X_OFFSET
        panel_rect = pygame.Rect(
            panel_x,
            self.margin,
            self.panel_width - _PANEL_X_OFFSET,
            self.grid_width,
        )
        pygame.draw.rect(self.screen, LIGHT_GRAY, panel_rect, border_radius=10)
        pygame.draw.rect(
            self.screen,
            WHITE,
            panel_rect.inflate(-8, -8),
            border_radius=10,
        )

        x = panel_x + 16
        y = self.margin + 18
        self.screen.blit(
            self.fonts.title.render("풀이 과정", True, PRIMARY_DARK), (x, y)
        )
        y += 38
        if self.result.status is SolveStatus.SOLVED_MULTIPLE:
            y = self._draw_wrapped(
                "복수해 · 최종 보드는 가능한 해 중 하나입니다.",
                x,
                y,
                color=ORANGE,
            )
        counter = f"{self.current_step_index + 1} / {len(self.result.steps)} 단계"
        self.screen.blit(self.fonts.heading.render(counter, True, BLACK), (x, y))
        y += 32

        step = self.current_step
        kind_label = _STEP_LABELS[step.kind]
        self.screen.blit(self.fonts.heading.render(kind_label, True, PRIMARY), (x, y))
        y += 28
        if step.deduction is not None:
            label = _technique_label(step)
            y = self._draw_wrapped(label, x, y, color=ACCENT)
        if step.depth:
            self.screen.blit(
                self.fonts.button.render("한 단계 가정 중", True, ORANGE),
                (x, y),
            )
            y += 25

        pygame.draw.line(
            self.screen,
            LIGHT_GRAY,
            (x, y + 2),
            (panel_rect.right - 16, y + 2),
            width=1,
        )
        y += 18
        if step.deduction is None:
            y = self._draw_wrapped(step.message or kind_label, x, y, color=GRAY)
        else:
            y = self._draw_detail_field("사유", _deduction_reason(step), x, y)
            for label, items in _deduction_effect_groups(step.deduction):
                y += 8
                y = self._draw_effect_field(label, items, x, y)

        if step.depth and step.assumption is not None:
            y += 10
            self.screen.blit(
                self.fonts.button.render("활성 가정", True, ORANGE), (x, y)
            )
            y += 22
            row, col = step.assumption.cell
            text = f"R{row + 1}C{col + 1} = {step.assumption.value}"
            self.screen.blit(self.fonts.body.render(text, True, GRAY), (x, y))

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

        help_text = "←/→ 단계 · Space 재생 · Esc 편집"
        help_surface = self.fonts.body.render(help_text, True, GRAY)
        self.screen.blit(
            help_surface,
            help_surface.get_rect(
                center=(panel_rect.centerx, self.previous_button.rect.top - 15)
            ),
        )

    def _draw_wrapped(
        self,
        text: str,
        x: int,
        y: int,
        *,
        color: tuple[int, int, int],
    ) -> int:
        max_width = self.panel_width - _PANEL_X_OFFSET - 32
        for line in wrap_text(text, self.fonts.body, max_width):
            self.screen.blit(self.fonts.body.render(line, True, color), (x, y))
            y += 20
        return y

    def _draw_detail_field(self, label: str, text: str, x: int, y: int) -> int:
        """라벨이 붙은 설명 필드 하나를 그린다."""

        self.screen.blit(self.fonts.button.render(label, True, PRIMARY), (x, y))
        y += 22
        return self._draw_wrapped(text, x, y, color=GRAY)

    def _draw_effect_field(
        self,
        label: str,
        items: tuple[str, ...],
        x: int,
        y: int,
    ) -> int:
        """각 항목을 유지하면서 변경된 칸을 간결하게 그린다."""

        self.screen.blit(self.fonts.button.render(label, True, PRIMARY), (x, y))
        y += 22
        max_width = self.panel_width - _PANEL_X_OFFSET - 32
        for line in _pack_effect_items(items, self.fonts.body, max_width):
            self.screen.blit(self.fonts.body.render(line, True, GRAY), (x, y))
            y += 20
        return y

    def _navigate(self, offset: int) -> bool:
        target = max(
            0,
            min(len(self.result.steps) - 1, self.current_step_index + offset),
        )
        if target == self.current_step_index:
            return False
        self.current_step_index = target
        self.autoplay_timer = 0.0
        return True

    def _set_index(self, index: int) -> None:
        self.current_step_index = max(0, min(len(self.result.steps) - 1, index))
        self.autoplay_timer = 0.0

    def _toggle_autoplay(self) -> None:
        self._clear_navigation_holds()
        if self.current_step_index == len(self.result.steps) - 1:
            self.current_step_index = 0
        self.autoplay_enabled = not self.autoplay_enabled
        self.autoplay_timer = 0.0

    def _begin_navigation_hold(
        self,
        source: _NavigationSource,
        offset: int,
    ) -> None:
        """한 번 이동한 뒤 일정한 반복 처리를 위해 입력을 기억한다."""

        if offset not in (-1, 1):
            raise ValueError("탐색 방향은 -1 또는 1이어야 합니다.")
        if source in self._held_navigation_sources:
            # 운영체제 키 반복이 생성한 KEYDOWN은 무시하고 프레임 시간으로 반복한다.
            return

        self.autoplay_enabled = False
        self._held_navigation_sources[source] = offset
        self._active_navigation_source = source
        self._navigation_repeat_timer = 0.0
        self._navigation_repeat_started = False
        self._navigate(offset)

    def _end_navigation_hold(self, source: _NavigationSource) -> None:
        """놓은 키나 마우스 버튼의 반복 처리를 멈춘다."""

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
        """지연 후 일정한 간격으로 누르고 있는 이동 입력을 처리한다."""

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
            self.autoplay_enabled = False
            changed = self._navigate(offset) or changed
            threshold = _NAVIGATION_REPEAT_INTERVAL
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
            self._set_index(len(self.result.steps) - 1)
        elif event.key == pygame.K_SPACE:
            self._toggle_autoplay()
        return None

    def _handle_keyup(self, event: pygame.event.Event) -> None:
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self._end_navigation_hold(("key", event.key))

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

    def _handle_mouse_up(self, event: pygame.event.Event) -> None:
        if event.button == 1:
            self._end_navigation_hold(("mouse", event.button))

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
            elif event.type == pygame.KEYUP:
                self._handle_keyup(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                action = self._handle_mouse_down(event)
                if action is not None:
                    return action
            elif event.type == pygame.MOUSEBUTTONUP:
                self._handle_mouse_up(event)
        return None

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
        return True

    async def run(self) -> Grid | None:
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
                return self.puzzle.grid
            if not self.running:
                break

            changed = bool(events)
            if timers_were_active:
                changed = self._update_navigation_hold(elapsed) or changed
                changed = self._update_autoplay(elapsed) or changed
            if changed:
                self.draw()
        return None

"""Read-only pygame view for a precomputed, structured solve trace."""

import pygame

from puzzle_common.coordinates import cell_name as _cell_name
from puzzle_common.playback import PlaybackDetails, PlaybackScreen
from puzzle_common.ui_style import (
    ACCENT,
    ACCENT_YELLOW,
    BLACK,
    CANDIDATE_GRAY,
    ORANGE,
    ORANGE_LIGHT,
    PRIMARY_DARK,
    PRIMARY_LIGHT,
    RED,
    WHITE,
)

from .board import Grid, Puzzle
from .solve_types import (
    SolveResult,
    SolveStatus,
    SolveStep,
    StepKind,
    Technique,
    TechniqueResult,
)
from .topology import SIZE, UNITS, Cell
from .ui_style import (
    draw_sudoku_grid_lines,
    get_fonts,
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

_CELL_SIZE = 60
_MARGIN = 50
_PANEL_WIDTH = 300
_PANEL_X_OFFSET = 10


def _deduction_effect_groups(
    deduction: TechniqueResult,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return labeled, atomic effect items from structured deduction data."""

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


def _deduction_reason(step: SolveStep) -> str:
    """Return producer-supplied reason prose; effects live in structured fields."""

    deduction = step.deduction
    if deduction is None:
        return step.message
    return deduction.explanation or step.message


def _technique_label(step: SolveStep) -> str:
    """Return the technique label, including the final Full House special case."""

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


class SudokuVisualizer(PlaybackScreen[Grid]):
    """Interpret Sudoku trace steps and render values, candidates and evidence."""

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
        self.cell_size = _CELL_SIZE
        self.margin = _MARGIN
        self.grid_width = SIZE * self.cell_size
        self.panel_width = _PANEL_WIDTH
        width = self.grid_width + 2 * self.margin + self.panel_width
        self.height = self.grid_width + 2 * self.margin
        super().__init__(
            frame_count=len(result.steps),
            edit_draft=puzzle.grid,
            size=(width, self.height),
            caption="스도쿠 풀이 과정",
            title="풀이 과정",
            board_rect=pygame.Rect(
                self.margin, self.margin, self.grid_width, self.grid_width
            ),
            panel_rect=pygame.Rect(
                self.margin + self.grid_width + _PANEL_X_OFFSET,
                self.margin,
                self.panel_width - _PANEL_X_OFFSET,
                self.grid_width,
            ),
            fonts=get_fonts(),
        )

    def _draw_board(self) -> None:
        pygame.draw.rect(self.screen, WHITE, self.board_rect)
        self._draw_cell_highlights()
        draw_sudoku_grid_lines(
            self.screen,
            (self.margin, self.margin),
            self.cell_size,
        )
        self._draw_values_and_candidates()

    def _presentation(self) -> PlaybackDetails:
        step = self.current_step
        annotations = []
        if step.deduction is not None:
            annotations.append((_technique_label(step), ACCENT))
        if step.depth:
            annotations.append(("한 단계 가정 중", ORANGE))
        return PlaybackDetails(
            title=_STEP_LABELS[step.kind],
            reason=_deduction_reason(step),
            effects=_deduction_effect_groups(step.deduction)
            if step.deduction is not None
            else (),
            status=("복수해 · 가능한 해 중 하나 표시", ORANGE, ORANGE_LIGHT)
            if self.result.status is SolveStatus.SOLVED_MULTIPLE
            else None,
            annotations=tuple(annotations),
            assumption=f"{_cell_name(step.assumption.cell)} = {step.assumption.value}"
            if step.depth and step.assumption is not None
            else "",
        )

    @property
    def current_step(self) -> SolveStep:
        return self.result.steps[self.current_step_index]

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

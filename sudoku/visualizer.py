"""Read-only pygame view for a precomputed, structured solve trace."""

import pygame

from puzzle_common.engine import SolveResult
from puzzle_common.playback import PlaybackDetails, PlaybackScreen
from puzzle_common.presentation import FrameKind, PlaybackFrame
from puzzle_common.ui_style import (
    ACCENT,
    ACCENT_YELLOW,
    BLACK,
    CANDIDATE_GRAY,
    ORANGE,
    PRIMARY_DARK,
    PRIMARY_LIGHT,
    RED,
    WHITE,
)

from .board import Grid, Puzzle
from .engine_adapter import SudokuSnapshot
from .presentation import describe_frame
from .solve_types import (
    Assignment,
    ContradictionWitness,
    TechniqueResult,
)
from .topology import SIZE, UNITS
from .ui_style import (
    draw_sudoku_grid_lines,
    get_fonts,
)


class SudokuVisualizer(
    PlaybackScreen[
        Grid, SudokuSnapshot, TechniqueResult, Assignment, ContradictionWitness
    ]
):
    """Interpret Sudoku trace steps and render values, candidates and evidence."""

    def __init__(self, puzzle: Puzzle, result: SolveResult) -> None:
        if not isinstance(puzzle, Puzzle):
            raise TypeError("SudokuVisualizer는 Puzzle을 받아야 합니다.")
        self.puzzle = puzzle
        super().__init__(
            result=result,
            edit_draft=puzzle.grid,
            board_size=SIZE,
            caption="스도쿠 풀이 과정",
            fonts=get_fonts(),
        )

    def _validate_frames(self) -> None:
        for frame in self.frames:
            snapshot = frame.snapshot
            if (
                not isinstance(snapshot, tuple)
                or len(snapshot) != 2
                or any(
                    not isinstance(board, tuple)
                    or len(board) != SIZE
                    or any(
                        not isinstance(row, tuple) or len(row) != SIZE for row in board
                    )
                    for board in snapshot
                )
            ):
                raise TypeError(
                    "SudokuVisualizer에는 스도쿠 grid/candidates가 필요합니다."
                )
            grid, candidates = snapshot
            if any(
                type(value) is not int or not 0 <= value <= SIZE
                for row in grid
                for value in row
            ):
                raise TypeError("스도쿠 grid는 0~9 정수로 구성되어야 합니다.")
            if any(
                not isinstance(values, frozenset)
                or any(
                    type(value) is not int or not 1 <= value <= SIZE for value in values
                )
                for row in candidates
                for values in row
            ):
                raise TypeError("스도쿠 후보는 1~9 정수의 frozenset이어야 합니다.")
            if (
                frame.deduction is not None
                and not isinstance(frame.deduction, TechniqueResult)
                or frame.contradiction is not None
                and not isinstance(frame.contradiction, ContradictionWitness)
                or frame.assumption is not None
                and not isinstance(frame.assumption, Assignment)
                or any(
                    not isinstance(decision, Assignment)
                    for decision in frame.candidates
                )
            ):
                raise TypeError("SudokuVisualizer에는 스도쿠 추론과 가정이 필요합니다.")
        if self.frames[0].snapshot[0] != self.puzzle.grid:
            raise ValueError("풀이 결과가 전달된 문제에서 생성되지 않았습니다.")

    def _draw_board(self, frame: PlaybackFrame) -> None:
        pygame.draw.rect(self.screen, WHITE, self.board_rect)
        self._draw_cell_highlights(frame)
        draw_sudoku_grid_lines(
            self.screen,
            self.board_origin,
            self.cell_size,
        )
        self._draw_values_and_candidates(frame)

    def _presentation(self, frame: PlaybackFrame) -> PlaybackDetails:
        return describe_frame(frame, self.result)

    def _draw_cell_highlights(self, step: PlaybackFrame) -> None:
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

        if step.active_assumption is not None or step.kind is FrameKind.REFUTATION:
            decision_color = RED if step.kind is FrameKind.REFUTATION else ORANGE
            self._fill_cell(step.assumption.cell, (*decision_color, 80))
            if step.active_assumption is not None:
                self._outline_cell(step.assumption.cell, ORANGE, width=3)

    def _draw_values_and_candidates(self, step: PlaybackFrame) -> None:
        assumption_cells = (
            {step.assumption.cell}
            if step.active_assumption is not None and step.assumption is not None
            else set()
        )
        removed_by_cell = {
            elimination.cell: elimination.values
            for elimination in (step.deduction.eliminations if step.deduction else ())
        }

        for row in range(SIZE):
            for col in range(SIZE):
                value = step.snapshot[0][row][col]
                center = self.layout.cell_rect((row, col)).center
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

                candidates = step.snapshot[1][row][col]
                removed = removed_by_cell.get((row, col), frozenset())
                self._draw_candidate_marks(row, col, candidates, removed)

    def _draw_candidate_marks(
        self,
        row: int,
        col: int,
        candidates: frozenset[int],
        removed: frozenset[int],
    ) -> None:
        rect = self.layout.cell_rect((row, col))
        for value in range(1, SIZE + 1):
            if value not in candidates and value not in removed:
                continue
            mark_row, mark_col = divmod(value - 1, 3)
            center = (
                rect.left + (mark_col * 2 + 1) * self.cell_size // 6,
                rect.top + (mark_row * 2 + 1) * self.cell_size // 6,
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

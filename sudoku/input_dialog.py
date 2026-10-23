"""Sudoku number editing and validation for the shared input screen."""

import pygame

from puzzle_common.input_dialog import InputDialog
from puzzle_common.ui_style import ACCENT_YELLOW, ACCENT_YELLOW_LIGHT, BLACK, RED

from .board import InvalidBoardError, Puzzle, find_conflicting_cells, validate_grid
from .matrix_input import OCR_MATRIX_PROMPT
from .matrix_parser import MatrixParseError, parse_matrix_json
from .puzzle_catalog import load_puzzle_catalog
from .topology import SIZE
from .ui_style import draw_conflict_cells, draw_sudoku_grid_lines, get_fonts


class SudokuInputDialog(InputDialog[Puzzle]):
    """Edit numbers and report conflicts using the common input UI."""

    title = "스도쿠 문제 입력"
    prompt = OCR_MATRIX_PROMPT
    json_description = "복사한 9×9 JSON을 아래 칸에 붙여넣고 불러오기를 누르세요."
    direct_instructions = (
        "칸 선택 · 1~9 입력 · 0/Delete 삭제",
        "화살표/Tab 이동 · C/R 전체 삭제 · S 시작",
    )
    parse_error = MatrixParseError
    start_keys = (*InputDialog.start_keys, pygame.K_s)

    def __init__(
        self,
        initial_board: object | None = None,
        initial_error: str | None = None,
    ) -> None:
        self.board = [[0] * SIZE for _ in range(SIZE)]
        if initial_board is not None:
            self.board = [list(row) for row in validate_grid(initial_board)]
        self.conflicting_cells = find_conflicting_cells(self.board)
        self.puzzle_catalog = load_puzzle_catalog()
        super().__init__(
            get_fonts(), tuple(self.puzzle_catalog), initial_error, board_size=SIZE
        )

    def _handle_editor_key(self, event: pygame.event.Event) -> bool:
        if self._handle_grid_navigation(event):
            return True
        if event.key in (pygame.K_r, pygame.K_c):
            self._replace_board([[0] * SIZE for _ in range(SIZE)])
        elif self.selected_cell is not None:
            self._handle_cell_input(event)
        return False

    def _replace_board(self, grid: object) -> None:
        """Atomically replace the editable draft after structural validation."""

        normalized = validate_grid(grid)
        self.board = [list(row) for row in normalized]
        self.conflicting_cells = find_conflicting_cells(normalized)
        self.selected_cell = None
        self._clear_message()

    def _set_cell(self, row: int, col: int, value: int) -> None:
        if self.board[row][col] == value:
            return
        self.board[row][col] = value
        self.conflicting_cells = find_conflicting_cells(self.board)
        self._clear_message()

    def _draw_grid(self) -> None:
        draw_conflict_cells(self.screen, self.conflicting_cells, self.layout)
        if self.selected_cell is not None:
            rect = self.layout.cell_rect(self.selected_cell).inflate(-6, -6)
            color = (
                RED if self.selected_cell in self.conflicting_cells else ACCENT_YELLOW
            )
            pygame.draw.rect(self.screen, color, rect, width=3)
            if color == ACCENT_YELLOW:
                fill = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                fill.fill((*ACCENT_YELLOW_LIGHT, 60))
                self.screen.blit(fill, rect.topleft)

        draw_sudoku_grid_lines(
            self.screen,
            (self.grid_start_x, self.grid_start_y),
            self.cell_size,
        )
        for row in range(SIZE):
            for col in range(SIZE):
                value = self.board[row][col]
                if not value:
                    continue
                color = RED if (row, col) in self.conflicting_cells else BLACK
                rendered = self.fonts.number.render(str(value), True, color)
                center = self.layout.cell_rect((row, col)).center
                self.screen.blit(rendered, rendered.get_rect(center=center))

    def _load_json_text(self, text: str) -> None:
        """Parse first, then atomically replace the draft with validated JSON."""

        grid = parse_matrix_json(text)
        self._replace_board(grid)
        if self.conflicting_cells:
            self._show_error(
                "JSON은 불러왔지만 중복 숫자가 있습니다. 빨간 칸을 원본과 대조해 수정하세요."
            )
        else:
            self._show_notice("9×9 JSON을 불러왔습니다. 원본 이미지와 확인하세요.")

    def _create_puzzle(self) -> Puzzle | None:
        if not any(value for row in self.board for value in row):
            self._show_error("최소 한 개 이상의 초기 숫자를 입력하세요.")
            return None
        if self.conflicting_cells:
            self._show_error("같은 행·열·박스에 중복된 숫자가 있습니다.")
            return None
        try:
            puzzle = Puzzle(self.board)
        except InvalidBoardError as exc:
            self._show_error(str(exc))
            return None
        return puzzle

    def _load_preset(self, index: int) -> None:
        difficulty = self.preset_names[index]
        self._replace_board(self.puzzle_catalog[difficulty])
        self._show_notice(f"{difficulty} 퍼즐을 불러왔습니다.")

    def _handle_cell_input(self, event: pygame.event.Event) -> None:
        assert self.selected_cell is not None
        row, col = self.selected_cell
        if event.key in (
            pygame.K_DELETE,
            pygame.K_BACKSPACE,
            pygame.K_0,
            pygame.K_KP0,
        ):
            self._set_cell(row, col, 0)
        elif pygame.K_1 <= event.key <= pygame.K_9:
            self._set_cell(row, col, event.key - pygame.K_0)
        elif pygame.K_KP1 <= event.key <= pygame.K_KP9:
            self._set_cell(row, col, event.key - pygame.K_KP0)

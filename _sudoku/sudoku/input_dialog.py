"""Editable Sudoku input screen, including strict external-AI JSON paste."""

from collections.abc import Callable, Iterable

import pygame

from .board import (
    InvalidBoardError,
    Puzzle,
    find_conflicting_cells,
    validate_grid,
)
from .matrix_input import (
    OCR_MATRIX_PROMPT,
    ClipboardError,
    copy_text,
    paste_text,
)
from .matrix_parser import MatrixParseError, parse_matrix_json
from .puzzle_catalog import load_puzzle_catalog
from .runtime import next_frame
from .topology import SIZE, Cell
from .ui_components import Button
from .ui_style import (
    ACCENT,
    ACCENT_YELLOW,
    ACCENT_YELLOW_LIGHT,
    APP_BACKGROUND,
    BLACK,
    BORDER,
    GRAY,
    LIGHT_GRAY,
    PRIMARY_DARK,
    RED,
    SURFACE_HOVER,
    SURFACE_SUBTLE,
    WHITE,
    configure_display,
    draw_conflict_cells,
    draw_sudoku_grid_lines,
    get_fonts,
    wrap_text,
)
from .web_text_dialog import (
    WebTextDialog,
    WebTextDialogError,
    is_web_runtime,
    open_json_dialog,
    open_prompt_dialog,
)

_CELL_SIZE = 60
_MARGIN = 45
_PANEL_WIDTH = 300
_PANEL_GAP = 30
_GRID_START_Y = 70
_DIALOG_WIDTH = SIZE * _CELL_SIZE + _PANEL_WIDTH + _PANEL_GAP + 2 * _MARGIN
_DIALOG_HEIGHT = 2 * _GRID_START_Y + SIZE * _CELL_SIZE
_PANEL_PADDING = 18
_BUTTON_HEIGHT = 42
_BUTTON_SPACING = 9
_BUTTON_ROW_SPACING = 10
_BUTTONS_PER_ROW = 3
_ERROR_MESSAGE_SPACING = 22


class SudokuInputDialog:
    """Collect and validate a puzzle before it enters the solver."""

    def __init__(
        self,
        initial_board: object | None = None,
        initial_error: str | None = None,
    ) -> None:
        self._init_screen()
        self._init_fonts()
        self._init_layout()
        self._init_state(initial_board, initial_error)
        self._init_buttons()

    def _init_screen(self) -> None:
        screen_size = (_DIALOG_WIDTH, _DIALOG_HEIGHT)
        self.screen = configure_display(screen_size, "스도쿠 문제 입력")

    def _init_fonts(self) -> None:
        self.fonts = get_fonts()

    def _init_layout(self) -> None:
        self.cell_size = _CELL_SIZE
        self.grid_width = SIZE * self.cell_size
        self.grid_start_x = _MARGIN
        self.grid_start_y = _GRID_START_Y
        self.panel_x = self.grid_start_x + self.grid_width + _PANEL_GAP
        self.panel_inner_width = _PANEL_WIDTH - 2 * _PANEL_PADDING

    def _init_state(
        self, initial_board: object | None, initial_error: str | None
    ) -> None:
        self.board = [[0] * SIZE for _ in range(SIZE)]
        if initial_board is not None:
            normalized = validate_grid(initial_board)
            self.board = [list(row) for row in normalized]
        self.selected_cell: Cell | None = None
        self.running = True
        self.validation_error = initial_error
        self.notice_message: str | None = None
        self.conflicting_cells = find_conflicting_cells(self.board)
        self._web_text_dialog: WebTextDialog | None = None

    def _init_buttons(self) -> None:
        self.puzzle_catalog = load_puzzle_catalog()
        self.difficulties = tuple(self.puzzle_catalog)
        cols = min(_BUTTONS_PER_ROW, len(self.difficulties))
        rows = (len(self.difficulties) + cols - 1) // cols
        spacing = _BUTTON_SPACING
        button_width = (self.panel_inner_width - (cols - 1) * spacing) // cols
        button_start_y = self.grid_start_y + 44

        self.buttons: list[Button] = []
        for index, difficulty in enumerate(self.difficulties):
            row, col = divmod(index, cols)
            x = self.panel_x + _PANEL_PADDING + col * (button_width + spacing)
            y = button_start_y + row * (_BUTTON_HEIGHT + _BUTTON_ROW_SPACING)
            self.buttons.append(
                Button(
                    pygame.Rect(
                        x,
                        y,
                        button_width,
                        _BUTTON_HEIGHT,
                    ),
                    difficulty,
                    SURFACE_SUBTLE,
                    self.fonts.button,
                    text_color=BLACK,
                    hover_color=SURFACE_HOVER,
                    border_color=BORDER,
                )
            )

        difficulty_bottom = (
            button_start_y
            + (rows - 1) * (_BUTTON_HEIGHT + _BUTTON_ROW_SPACING)
            + _BUTTON_HEIGHT
        )

        action_y = difficulty_bottom + 18
        half_width = (self.panel_inner_width - spacing) // 2
        action_x = self.panel_x + _PANEL_PADDING
        prompt_label = "프롬프트 보기" if is_web_runtime() else "프롬프트 복사"
        json_label = "JSON 입력" if is_web_runtime() else "JSON 붙여넣기"
        self.copy_prompt_button = Button(
            pygame.Rect(
                action_x,
                action_y,
                half_width,
                _BUTTON_HEIGHT,
            ),
            prompt_label,
            SURFACE_SUBTLE,
            self.fonts.button,
            text_color=PRIMARY_DARK,
            hover_color=SURFACE_HOVER,
            border_color=BORDER,
        )
        self.paste_button = Button(
            pygame.Rect(
                action_x + half_width + spacing,
                action_y,
                half_width,
                _BUTTON_HEIGHT,
            ),
            json_label,
            SURFACE_SUBTLE,
            self.fonts.button,
            text_color=PRIMARY_DARK,
            hover_color=SURFACE_HOVER,
            border_color=BORDER,
        )
        self.start_button = Button(
            pygame.Rect(
                action_x,
                action_y + _BUTTON_HEIGHT + 16,
                self.panel_inner_width,
                _BUTTON_HEIGHT + 4,
            ),
            "풀이 시작",
            PRIMARY_DARK,
            self.fonts.button,
        )

    def _show_error(self, message: str) -> None:
        self.validation_error = message
        self.notice_message = None

    def _show_notice(self, message: str) -> None:
        self.validation_error = None
        self.notice_message = message

    def _clear_message(self) -> None:
        self.validation_error = None
        self.notice_message = None

    def _replace_board(self, grid: object) -> None:
        """Atomically replace the editable draft after structural validation."""

        normalized = validate_grid(grid)
        self.board = [list(row) for row in normalized]
        self.conflicting_cells = find_conflicting_cells(normalized)
        self.selected_cell = None
        self._clear_message()

    def _set_cell(self, row: int, col: int, value: int) -> None:
        self.board[row][col] = value
        self.conflicting_cells = find_conflicting_cells(self.board)
        self._clear_message()

    def draw(self) -> None:
        self.screen.fill(APP_BACKGROUND)
        self._draw_title()
        self._draw_grid()
        self._draw_panel()
        pygame.display.flip()

    def _draw_title(self) -> None:
        title = self.fonts.title.render("스도쿠 문제 입력", True, PRIMARY_DARK)
        self.screen.blit(
            title,
            title.get_rect(center=(_DIALOG_WIDTH // 2, 40)),
        )

    def _draw_grid(self) -> None:
        grid_rect = pygame.Rect(
            self.grid_start_x,
            self.grid_start_y,
            self.grid_width,
            self.grid_width,
        )
        pygame.draw.rect(
            self.screen,
            LIGHT_GRAY,
            grid_rect.move(0, 3),
            border_radius=4,
        )
        pygame.draw.rect(self.screen, WHITE, grid_rect)
        draw_conflict_cells(
            self.screen,
            self.conflicting_cells,
            (self.grid_start_x, self.grid_start_y),
            self.cell_size,
        )
        if self.selected_cell is not None:
            row, col = self.selected_cell
            x = self.grid_start_x + col * self.cell_size
            y = self.grid_start_y + row * self.cell_size
            rect = pygame.Rect(x + 3, y + 3, self.cell_size - 6, self.cell_size - 6)
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
                center = (
                    self.grid_start_x + col * self.cell_size + self.cell_size // 2,
                    self.grid_start_y + row * self.cell_size + self.cell_size // 2,
                )
                self.screen.blit(rendered, rendered.get_rect(center=center))

    def _draw_panel(self) -> None:
        panel_rect = pygame.Rect(
            self.panel_x,
            self.grid_start_y,
            _PANEL_WIDTH,
            SIZE * self.cell_size,
        )
        pygame.draw.rect(
            self.screen,
            LIGHT_GRAY,
            panel_rect.move(0, 3),
            border_radius=14,
        )
        pygame.draw.rect(self.screen, WHITE, panel_rect, border_radius=14)
        pygame.draw.rect(
            self.screen,
            BORDER,
            panel_rect,
            width=1,
            border_radius=14,
        )

        x = self.panel_x + _PANEL_PADDING
        title = self.fonts.heading.render("예제 문제", True, BLACK)
        self.screen.blit(title, (x, self.grid_start_y + 15))

        mouse_pos = pygame.mouse.get_pos()
        for button in (
            *self.buttons,
            self.copy_prompt_button,
            self.paste_button,
            self.start_button,
        ):
            button.update_hover(mouse_pos)
            button.draw(self.screen)

        self._draw_instructions()
        self._draw_message()

    def _draw_instructions(self) -> None:
        x = self.panel_x + _PANEL_PADDING
        y = self.start_button.rect.bottom + 24
        divider_right = self.panel_x + _PANEL_WIDTH - _PANEL_PADDING
        pygame.draw.line(self.screen, LIGHT_GRAY, (x, y - 10), (divider_right, y - 10))
        ai_instructions = (
            ("프롬프트를 열어 직접 선택·복사", "JSON 입력 창에 직접 붙여넣기")
            if is_web_runtime()
            else ("프롬프트를 이미지와 함께 요청", "JSON 버튼 또는 Ctrl+V로 붙여넣기")
        )
        sections = (
            (
                "직접 입력",
                ("칸 선택 · 1~9 입력 · 0/Delete 삭제", "화살표 이동 · C/R 전체 삭제"),
            ),
            (
                "외부 AI/OCR",
                ai_instructions,
            ),
            ("시작 / 종료", ("Enter/S로 풀이 · ESC로 종료",)),
        )
        for title, lines in sections:
            self.screen.blit(
                self.fonts.button.render(title, True, PRIMARY_DARK), (x, y)
            )
            y += 23
            for line in lines:
                for wrapped in wrap_text(
                    f"• {line}", self.fonts.body, self.panel_inner_width
                ):
                    self.screen.blit(
                        self.fonts.body.render(wrapped, True, GRAY), (x, y)
                    )
                    y += 20
            y += 10
        self.instructions_bottom = y

    def _draw_message(self) -> None:
        message = self.validation_error or self.notice_message
        if not message:
            return
        color = RED if self.validation_error else ACCENT
        y = self.instructions_bottom + 4
        center_x = self.panel_x + _PANEL_WIDTH // 2
        for line in wrap_text(message, self.fonts.body, self.panel_inner_width - 8):
            rendered = self.fonts.body.render(line, True, color)
            self.screen.blit(rendered, rendered.get_rect(center=(center_x, y)))
            y += _ERROR_MESSAGE_SPACING

    def _handle_events(
        self,
        events: Iterable[pygame.event.Event],
    ) -> Puzzle | None:
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return None
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                result = self._handle_mouse_click(event.pos)
                if result is not None:
                    return result
            if event.type == pygame.KEYDOWN:
                result = self._handle_keydown(event)
                if result is not None:
                    return result
        return None

    def _handle_mouse_click(self, position: tuple[int, int]) -> Puzzle | None:
        for index, button in enumerate(self.buttons):
            if button.is_clicked(position):
                self._load_difficulty_puzzle(index)
                return None
        if self.copy_prompt_button.is_clicked(position):
            self._handle_prompt_action()
            return None
        if self.paste_button.is_clicked(position):
            self._handle_json_action()
            return None
        if self.start_button.is_clicked(position):
            return self._handle_start()
        if self._point_in_grid(position):
            mouse_x, mouse_y = position
            self.selected_cell = (
                (mouse_y - self.grid_start_y) // self.cell_size,
                (mouse_x - self.grid_start_x) // self.cell_size,
            )
        return None

    def _handle_keydown(self, event: pygame.event.Event) -> Puzzle | None:
        if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
            self._handle_json_action()
            return None
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_s):
            return self._handle_start()
        if event.key == pygame.K_ESCAPE:
            self.running = False
            return None
        if event.key in (pygame.K_r, pygame.K_c):
            self._replace_board([[0] * SIZE for _ in range(SIZE)])
            return None
        if self.selected_cell is not None:
            self._handle_cell_input(event)
        return None

    def _handle_prompt_action(self) -> None:
        if is_web_runtime():
            self._open_web_dialog(lambda: open_prompt_dialog(OCR_MATRIX_PROMPT))
            return
        self._copy_ai_prompt()

    def _copy_ai_prompt(self) -> None:
        try:
            copy_text(OCR_MATRIX_PROMPT)
        except ClipboardError as exc:
            self._show_error(str(exc))
            return
        self._show_notice("AI/OCR용 프롬프트와 예시를 복사했습니다.")

    def _handle_json_action(self) -> None:
        if is_web_runtime():
            self._open_web_dialog(open_json_dialog)
            return
        self._paste_matrix()

    def _paste_matrix(self) -> None:
        """Read, fully parse, then atomically replace the draft board."""

        try:
            text = paste_text()
            self._load_matrix_text(text)
        except (ClipboardError, MatrixParseError) as exc:
            self._show_error(str(exc))

    def _load_matrix_text(self, text: str) -> None:
        """Parse first, then atomically replace the draft with validated JSON."""

        grid = parse_matrix_json(text)
        self._replace_board(grid)
        if self.conflicting_cells:
            self._show_error(
                "JSON은 불러왔지만 중복 숫자가 있습니다. 빨간 칸을 원본과 대조해 수정하세요."
            )
        else:
            self._show_notice("9×9 JSON을 불러왔습니다. 원본 이미지와 확인하세요.")

    def _open_web_dialog(self, factory: Callable[[], WebTextDialog]) -> None:
        if self._web_text_dialog is not None:
            return
        try:
            self._web_text_dialog = factory()
        except WebTextDialogError as exc:
            self._show_error(str(exc))

    def _poll_web_text_dialog(self) -> bool:
        dialog = self._web_text_dialog
        if dialog is None:
            return False
        try:
            result = dialog.poll()
            if result is None:
                return False
            if not result.submitted:
                self._web_text_dialog = None
                return True
            try:
                self._load_matrix_text(result.text)
            except MatrixParseError as exc:
                dialog.show_error(str(exc))
                return False
            dialog.close()
            self._web_text_dialog = None
            return True
        except WebTextDialogError as exc:
            try:
                dialog.close()
            except WebTextDialogError as close_exc:
                exc = WebTextDialogError(f"{exc} {close_exc}")
            self._web_text_dialog = None
            self._show_error(str(exc))
            return True

    def _close_web_text_dialog(self) -> None:
        dialog = self._web_text_dialog
        self._web_text_dialog = None
        if dialog is None:
            return
        try:
            dialog.close()
        except WebTextDialogError as exc:
            self._show_error(str(exc))

    def _handle_start(self) -> Puzzle | None:
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
        self._clear_message()
        self.running = False
        return puzzle

    def _load_difficulty_puzzle(self, index: int) -> None:
        difficulty = self.difficulties[index]
        self._replace_board(self.puzzle_catalog[difficulty])
        self._show_notice(f"{difficulty} 퍼즐을 불러왔습니다.")

    def _point_in_grid(self, position: tuple[int, int]) -> bool:
        x, y = position
        return (
            self.grid_start_x <= x < self.grid_start_x + self.grid_width
            and self.grid_start_y <= y < self.grid_start_y + self.grid_width
        )

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
        elif event.key == pygame.K_UP and row > 0:
            self.selected_cell = (row - 1, col)
        elif event.key == pygame.K_DOWN and row < SIZE - 1:
            self.selected_cell = (row + 1, col)
        elif event.key == pygame.K_LEFT and col > 0:
            self.selected_cell = (row, col - 1)
        elif event.key == pygame.K_RIGHT and col < SIZE - 1:
            self.selected_cell = (row, col + 1)

    async def run(self) -> Puzzle | None:
        clock = pygame.time.Clock()
        self.draw()
        try:
            while self.running:
                await next_frame(clock)
                modal_was_open = self._web_text_dialog is not None
                dialog_changed = self._poll_web_text_dialog()
                events = pygame.event.get()
                if modal_was_open:
                    events = [event for event in events if event.type == pygame.QUIT]
                result = self._handle_events(events)
                if result is not None:
                    return result
                if self.running and (events or dialog_changed):
                    self.draw()
            return None
        finally:
            self._close_web_text_dialog()

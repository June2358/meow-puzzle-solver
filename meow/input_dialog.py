"""Editable MEOW Queens region input with strict external-vision JSON paste."""

from collections.abc import Callable, Iterable
from typing import Final

import pygame

from .input_draft import IncompleteDraftError, RegionDraft
from .matrix_input import (
    VISION_REGION_PROMPT,
    ClipboardError,
    copy_text,
    paste_text,
)
from .model import MAX_PUZZLE_SIZE, Cell, InvalidRegionMapError, Puzzle
from .parser import PuzzleParseError, parse_puzzle_json
from .puzzle_catalog import PRESET_NAMES, load_preset
from .runtime import next_frame
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
    draw_region_grid_lines,
    get_fonts,
    region_palette,
    wrap_text,
)
from .web_text_dialog import (
    WebTextDialog,
    WebTextDialogError,
    is_web_runtime,
    open_json_dialog,
    open_prompt_dialog,
)

DEFAULT_DRAFT_SIZE: Final = 8
MIN_DIRECT_SIZE: Final = 1
MAX_DIRECT_SIZE: Final = MAX_PUZZLE_SIZE

_BOARD_AREA = 540
_MARGIN = 45
_PANEL_WIDTH = 320
_PANEL_GAP = 30
_GRID_START_Y = 70
_DIALOG_WIDTH = _BOARD_AREA + _PANEL_WIDTH + _PANEL_GAP + 2 * _MARGIN
_DIALOG_HEIGHT = 2 * _GRID_START_Y + _BOARD_AREA
_PANEL_PADDING = 18
_BUTTON_HEIGHT = 40
_BUTTON_SPACING = 9
_PRESET_COLUMNS = 3
_MESSAGE_SPACING = 20


class MeowInputDialog:
    """Collect one valid variable-size Queens region puzzle."""

    def __init__(
        self,
        initial_grid: object | None = None,
    ) -> None:
        self.screen = configure_display(
            (_DIALOG_WIDTH, _DIALOG_HEIGHT),
            "MEOW · Queens 문제 입력",
        )
        self.fonts = get_fonts()
        self.draft = (
            RegionDraft.empty(DEFAULT_DRAFT_SIZE)
            if initial_grid is None
            else RegionDraft(initial_grid)
        )
        self.selected_cell: Cell | None = None
        self.running = True
        self.validation_error: str | None = None
        self.notice_message: str | None = None
        self.size_text = str(self.draft.size)
        self.size_focused = False
        self._replace_size_on_digit = False
        self._dragging = False
        self._drag_label: str | None = None
        self._web_text_dialog: WebTextDialog | None = None

        self.panel_x = _MARGIN + _BOARD_AREA + _PANEL_GAP
        self.panel_inner_x = self.panel_x + _PANEL_PADDING
        self.panel_inner_width = _PANEL_WIDTH - 2 * _PANEL_PADDING
        self._update_grid_layout()
        self._init_buttons()

    def _update_grid_layout(self) -> None:
        self.cell_size = min(90, max(1, _BOARD_AREA // self.draft.size))
        self.grid_width = self.cell_size * self.draft.size
        self.grid_start_x = _MARGIN + (_BOARD_AREA - self.grid_width) // 2
        self.grid_start_y = _GRID_START_Y + (_BOARD_AREA - self.grid_width) // 2

    def _init_buttons(self) -> None:
        gap = _BUTTON_SPACING
        preset_button_width = (
            self.panel_inner_width - (_PRESET_COLUMNS - 1) * gap
        ) // _PRESET_COLUMNS
        preset_y = _GRID_START_Y + 42
        self.preset_buttons: list[Button] = []
        for index, name in enumerate(PRESET_NAMES):
            row, column = divmod(index, _PRESET_COLUMNS)
            self.preset_buttons.append(
                Button(
                    pygame.Rect(
                        self.panel_inner_x + column * (preset_button_width + gap),
                        preset_y + row * (_BUTTON_HEIGHT + gap),
                        preset_button_width,
                        _BUTTON_HEIGHT,
                    ),
                    name,
                    SURFACE_SUBTLE,
                    self.fonts.button,
                    text_color=BLACK,
                    hover_color=SURFACE_HOVER,
                    border_color=BORDER,
                )
            )

        self.size_field_rect = pygame.Rect(
            self.panel_inner_x + 52,
            _GRID_START_Y + 172,
            58,
            _BUTTON_HEIGHT,
        )
        new_grid_x = self.size_field_rect.right + gap
        self.new_grid_button = Button(
            pygame.Rect(
                new_grid_x,
                self.size_field_rect.top,
                self.panel_inner_x + self.panel_inner_width - new_grid_x,
                _BUTTON_HEIGHT,
            ),
            "빈 격자 만들기",
            SURFACE_SUBTLE,
            self.fonts.button,
            text_color=PRIMARY_DARK,
            hover_color=SURFACE_HOVER,
            border_color=BORDER,
        )

        tool_y = _GRID_START_Y + 254
        tool_button_width = (self.panel_inner_width - gap) // 2
        prompt_label = "프롬프트 보기" if is_web_runtime() else "프롬프트 복사"
        json_label = "JSON 입력" if is_web_runtime() else "JSON 붙여넣기"
        self.copy_prompt_button = Button(
            pygame.Rect(
                self.panel_inner_x,
                tool_y,
                tool_button_width,
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
                self.panel_inner_x + tool_button_width + gap,
                tool_y,
                tool_button_width,
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
                self.panel_inner_x,
                _GRID_START_Y + 312,
                self.panel_inner_width,
                _BUTTON_HEIGHT + 6,
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

    def _replace_draft(self, draft: RegionDraft, notice: str) -> None:
        """Atomically replace the visible draft with an already-valid value."""

        self.draft = draft
        self.selected_cell = None
        self.size_text = str(draft.size)
        self.size_focused = False
        self._replace_size_on_digit = False
        self._dragging = False
        self._drag_label = None
        self._update_grid_layout()
        self._show_notice(notice)

    def _set_cell(self, cell: Cell, label: str | None, *, advance: bool) -> None:
        changed = self.draft.with_cell(cell, label)
        self.selected_cell = cell
        if changed is self.draft:
            return
        self.draft = changed
        self._clear_message()
        if advance:
            self._move_linear(1)

    def _move_linear(self, offset: int) -> None:
        if self.selected_cell is None:
            self.selected_cell = (0, 0)
            return
        row, column = self.selected_cell
        index = row * self.draft.size + column
        target = max(0, min(self.draft.size * self.draft.size - 1, index + offset))
        self.selected_cell = divmod(target, self.draft.size)

    def _move_direction(self, row_offset: int, column_offset: int) -> None:
        if self.selected_cell is None:
            self.selected_cell = (0, 0)
            return
        row, column = self.selected_cell
        self.selected_cell = (
            max(0, min(self.draft.size - 1, row + row_offset)),
            max(0, min(self.draft.size - 1, column + column_offset)),
        )

    def draw(self) -> None:
        self.screen.fill(APP_BACKGROUND)
        self._draw_title()
        self._draw_grid()
        self._draw_panel()
        pygame.display.flip()

    def _draw_title(self) -> None:
        title = self.fonts.title.render("MEOW · Queens 문제 입력", True, PRIMARY_DARK)
        self.screen.blit(
            title,
            title.get_rect(center=(_DIALOG_WIDTH // 2, 35)),
        )

    def _draw_grid(self) -> None:
        board_panel = pygame.Rect(_MARGIN, _GRID_START_Y, _BOARD_AREA, _BOARD_AREA)
        pygame.draw.rect(
            self.screen,
            LIGHT_GRAY,
            board_panel.move(0, 3),
            border_radius=10,
        )
        pygame.draw.rect(self.screen, WHITE, board_panel, border_radius=10)

        colors = region_palette(self.draft.labels)
        label_font = (
            self.fonts.heading if self.cell_size >= 42 else self.fonts.candidate
        )
        for row in range(self.draft.size):
            for column in range(self.draft.size):
                label = self.draft.grid[row][column]
                rect = pygame.Rect(
                    self.grid_start_x + column * self.cell_size,
                    self.grid_start_y + row * self.cell_size,
                    self.cell_size,
                    self.cell_size,
                )
                pygame.draw.rect(self.screen, colors.get(label, WHITE), rect)
                if label is not None and self.cell_size >= 18:
                    text = self._fit_label(
                        label, label_font, max(1, self.cell_size - 5)
                    )
                    if text:
                        rendered = label_font.render(text, True, BLACK)
                        self.screen.blit(
                            rendered, rendered.get_rect(center=rect.center)
                        )

        if self.selected_cell is not None:
            row, column = self.selected_cell
            rect = pygame.Rect(
                self.grid_start_x + column * self.cell_size + 2,
                self.grid_start_y + row * self.cell_size + 2,
                max(1, self.cell_size - 4),
                max(1, self.cell_size - 4),
            )
            fill = pygame.Surface(rect.size, pygame.SRCALPHA)
            fill.fill((*ACCENT_YELLOW_LIGHT, 70))
            self.screen.blit(fill, rect.topleft)
            pygame.draw.rect(self.screen, ACCENT_YELLOW, rect, width=3)

        visible_grid = tuple(
            tuple(label or "" for label in row) for row in self.draft.grid
        )
        draw_region_grid_lines(
            self.screen,
            visible_grid,
            (self.grid_start_x, self.grid_start_y),
            self.cell_size,
        )

    @staticmethod
    def _fit_label(label: str, font: pygame.font.Font, width: int) -> str:
        if font.size(label)[0] <= width:
            return label
        content = label
        while content and font.size(content + "…")[0] > width:
            content = content[:-1]
        return content + "…" if content else ""

    def _draw_panel(self) -> None:
        panel_rect = pygame.Rect(
            self.panel_x,
            _GRID_START_Y,
            _PANEL_WIDTH,
            _BOARD_AREA,
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

        progress = (
            f"입력 {self.draft.filled_count}/{self.draft.size * self.draft.size} · "
            f"영역 {len(self.draft.labels)}/{self.draft.size}"
        )
        self.screen.blit(
            self.fonts.heading.render("예제 문제", True, BLACK),
            (self.panel_inner_x, _GRID_START_Y + 14),
        )
        progress_surface = self.fonts.candidate.render(progress, True, GRAY)
        self.screen.blit(
            progress_surface,
            progress_surface.get_rect(
                topright=(
                    self.panel_x + _PANEL_WIDTH - _PANEL_PADDING,
                    _GRID_START_Y + 19,
                )
            ),
        )

        mouse_pos = pygame.mouse.get_pos()
        for button in (
            *self.preset_buttons,
            self.new_grid_button,
            self.copy_prompt_button,
            self.paste_button,
            self.start_button,
        ):
            button.update_hover(mouse_pos)
            button.draw(self.screen)

        direct_y = _GRID_START_Y + 145
        self.screen.blit(
            self.fonts.body.render("직접 입력", True, PRIMARY_DARK),
            (self.panel_inner_x, direct_y),
        )
        size_label = self.fonts.body.render("크기 N", True, BLACK)
        self.screen.blit(
            size_label,
            size_label.get_rect(
                midleft=(self.panel_inner_x, self.size_field_rect.centery)
            ),
        )
        pygame.draw.rect(
            self.screen,
            WHITE if self.size_focused else SURFACE_SUBTLE,
            self.size_field_rect,
            border_radius=8,
        )
        pygame.draw.rect(
            self.screen,
            ACCENT if self.size_focused else BORDER,
            self.size_field_rect,
            width=2 if self.size_focused else 1,
            border_radius=8,
        )
        rendered_size = self.fonts.heading.render(self.size_text, True, BLACK)
        self.screen.blit(
            rendered_size,
            rendered_size.get_rect(center=self.size_field_rect.center),
        )

        self.screen.blit(
            self.fonts.body.render("이미지 / JSON", True, PRIMARY_DARK),
            (self.panel_inner_x, _GRID_START_Y + 227),
        )
        self._draw_instructions()
        self._draw_message()

    def _draw_instructions(self) -> None:
        y = self.start_button.rect.bottom + 24
        right = self.panel_x + _PANEL_WIDTH - _PANEL_PADDING
        pygame.draw.line(
            self.screen,
            LIGHT_GRAY,
            (self.panel_inner_x, y - 10),
            (right, y - 10),
        )
        lines = (
            (
                "A~Z 입력 · Delete/Backspace 삭제",
                "화살표/Tab 이동 · 채운 칸에서 드래그",
                "JSON 입력 창에 직접 붙여넣기",
                "Enter 시작 · Esc 종료",
            )
            if is_web_runtime()
            else (
                "A~Z 입력 · Delete/Backspace 삭제",
                "화살표/Tab 이동 · 채운 칸에서 드래그",
                "Ctrl+V JSON · Enter 시작 · Esc 종료",
            )
        )
        for line in lines:
            self.screen.blit(
                self.fonts.candidate.render(f"• {line}", True, GRAY),
                (self.panel_inner_x, y),
            )
            y += 20
        self.instructions_bottom = y

    def _draw_message(self) -> None:
        message = self.validation_error or self.notice_message
        if not message:
            return
        color = RED if self.validation_error else ACCENT
        y = self.instructions_bottom + 5
        bottom = _GRID_START_Y + _BOARD_AREA - 10
        for line in wrap_text(message, self.fonts.candidate, self.panel_inner_width):
            if y + self.fonts.candidate.get_linesize() > bottom:
                break
            self.screen.blit(
                self.fonts.candidate.render(line, True, color),
                (self.panel_inner_x, y),
            )
            y += _MESSAGE_SPACING

    def _handle_events(
        self,
        events: Iterable[pygame.event.Event],
    ) -> Puzzle | None:
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return None
            if event.type == pygame.WINDOWFOCUSLOST:
                self._dragging = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                result = self._handle_mouse_click(event.pos)
                if result is not None:
                    return result
            elif event.type == pygame.MOUSEMOTION and self._dragging:
                buttons = getattr(event, "buttons", (False, False, False))
                if buttons and buttons[0] and self._drag_label is not None:
                    cell = self._cell_at(event.pos)
                    if cell is not None:
                        self._set_cell(cell, self._drag_label, advance=False)
            elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self._dragging = False
            elif event.type == pygame.KEYDOWN:
                result = self._handle_keydown(event)
                if result is not None:
                    return result
        return None

    def _handle_mouse_click(self, position: tuple[int, int]) -> Puzzle | None:
        self.size_focused = False
        self._dragging = False
        for index, button in enumerate(self.preset_buttons):
            if button.is_clicked(position):
                self._load_preset(index)
                return None
        if self.new_grid_button.is_clicked(position):
            self._apply_size()
            return None
        if self.copy_prompt_button.is_clicked(position):
            self._handle_prompt_action()
            return None
        if self.paste_button.is_clicked(position):
            self._handle_json_action()
            return None
        if self.start_button.is_clicked(position):
            return self._handle_start()
        if self.size_field_rect.collidepoint(position):
            self.size_focused = True
            self._replace_size_on_digit = True
            return None

        cell = self._cell_at(position)
        if cell is not None:
            self.selected_cell = cell
            self._drag_label = self.draft.label_at(cell)
            self._dragging = self._drag_label is not None
        return None

    def _handle_keydown(self, event: pygame.event.Event) -> Puzzle | None:
        if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
            self._handle_json_action()
            return None
        if event.key == pygame.K_ESCAPE:
            self.running = False
            return None
        if self.size_focused:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._apply_size()
            elif event.key == pygame.K_TAB:
                self.size_focused = False
                self.selected_cell = self.selected_cell or (0, 0)
            else:
                self._handle_size_key(event)
            return None
        if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            return self._handle_start()
        self._handle_grid_key(event)
        return None

    def _handle_size_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_BACKSPACE:
            self.size_text = "" if self._replace_size_on_digit else self.size_text[:-1]
            self._replace_size_on_digit = False
            return
        text = getattr(event, "unicode", "")
        if len(text) == 1 and "0" <= text <= "9":
            self.size_text = (
                text if self._replace_size_on_digit else self.size_text + text
            )
            self._replace_size_on_digit = False

    def _handle_grid_key(self, event: pygame.event.Event) -> None:
        if event.key == pygame.K_TAB:
            self._move_linear(-1 if event.mod & pygame.KMOD_SHIFT else 1)
            return
        directions = {
            pygame.K_UP: (-1, 0),
            pygame.K_DOWN: (1, 0),
            pygame.K_LEFT: (0, -1),
            pygame.K_RIGHT: (0, 1),
        }
        direction = directions.get(event.key)
        if direction is not None:
            self._move_direction(*direction)
            return
        if self.selected_cell is None:
            return
        if event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self._set_cell(self.selected_cell, None, advance=False)
            self._drag_label = None
            return
        if event.mod & (pygame.KMOD_CTRL | pygame.KMOD_ALT):
            return
        text = getattr(event, "unicode", "").upper()
        if len(text) == 1 and "A" <= text <= "Z":
            cell = self.selected_cell
            self._set_cell(cell, text, advance=True)
            self._drag_label = text

    def _apply_size(self) -> None:
        try:
            size = int(self.size_text)
        except ValueError:
            self._show_error("크기 N은 정수여야 합니다.")
            return
        if not MIN_DIRECT_SIZE <= size <= MAX_DIRECT_SIZE:
            self._show_error(
                f"직접 입력 크기는 {MIN_DIRECT_SIZE}~{MAX_DIRECT_SIZE}여야 합니다."
            )
            return
        self._replace_draft(
            RegionDraft.empty(size),
            f"빈 {size}×{size} 격자를 만들었습니다.",
        )

    def _handle_prompt_action(self) -> None:
        if is_web_runtime():
            self._open_web_dialog(lambda: open_prompt_dialog(VISION_REGION_PROMPT))
            return
        self._copy_ai_prompt()

    def _copy_ai_prompt(self) -> None:
        try:
            copy_text(VISION_REGION_PROMPT)
        except ClipboardError as error:
            self._show_error(str(error))
            return
        self._show_notice("이미지 영역 전사용 프롬프트를 복사했습니다.")

    def _handle_json_action(self) -> None:
        if is_web_runtime():
            self._open_web_dialog(open_json_dialog)
            return
        self._paste_puzzle()

    def _paste_puzzle(self) -> None:
        """Parse completely before replacing any visible draft state."""

        try:
            text = paste_text()
            self._load_puzzle_text(text)
        except (ClipboardError, PuzzleParseError) as error:
            self._show_error(str(error))

    def _load_puzzle_text(self, text: str) -> None:
        """Parse first, then atomically replace the draft with validated JSON."""

        puzzle = parse_puzzle_json(text)
        self._replace_draft(
            RegionDraft(puzzle.region_grid),
            f"{puzzle.size}×{puzzle.size} JSON을 불러왔습니다. 원본 이미지와 확인하세요.",
        )

    def _open_web_dialog(self, factory: Callable[[], WebTextDialog]) -> None:
        if self._web_text_dialog is not None:
            return
        try:
            self._web_text_dialog = factory()
        except WebTextDialogError as error:
            self._show_error(str(error))

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
                self._load_puzzle_text(result.text)
            except PuzzleParseError as error:
                dialog.show_error(str(error))
                return False
            dialog.close()
            self._web_text_dialog = None
            return True
        except WebTextDialogError as error:
            try:
                dialog.close()
            except WebTextDialogError as close_error:
                error = WebTextDialogError(f"{error} {close_error}")
            self._web_text_dialog = None
            self._show_error(str(error))
            return True

    def _close_web_text_dialog(self) -> None:
        dialog = self._web_text_dialog
        self._web_text_dialog = None
        if dialog is None:
            return
        try:
            dialog.close()
        except WebTextDialogError as error:
            self._show_error(str(error))

    def _handle_start(self) -> Puzzle | None:
        empty = self.draft.first_empty()
        if empty is not None:
            self.selected_cell = empty
        try:
            puzzle = self.draft.to_puzzle()
        except (IncompleteDraftError, InvalidRegionMapError) as error:
            self._show_error(str(error))
            return None
        self._clear_message()
        self.running = False
        return puzzle

    def _load_preset(self, index: int) -> None:
        name = PRESET_NAMES[index]
        puzzle = load_preset(name)
        self._replace_draft(
            RegionDraft(puzzle.region_grid),
            f"{name} 문제를 불러왔습니다.",
        )

    def _cell_at(self, position: tuple[int, int]) -> Cell | None:
        x, y = position
        if not (
            self.grid_start_x <= x < self.grid_start_x + self.grid_width
            and self.grid_start_y <= y < self.grid_start_y + self.grid_width
        ):
            return None
        return (
            (y - self.grid_start_y) // self.cell_size,
            (x - self.grid_start_x) // self.cell_size,
        )

    async def run(self) -> Puzzle | None:
        """Wait for input until a valid Puzzle is confirmed or the app closes."""

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

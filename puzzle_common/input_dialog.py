"""One definition-driven editor with an immutable, normalized draft grid."""

from collections.abc import Callable, Iterable

import pygame

from .board import draw_board
from .clipboard import ClipboardError, copy_text, paste_text
from .drafts import save_draft
from .layout import TOUCH_GAP, TOUCH_SIZE, get_board_layout
from .puzzle import PuzzleDefinition
from .runtime import next_frame
from .ui_components import Button, draw_panel
from .ui_style import (
    ACCENT,
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
    Fonts,
    configure_display,
    get_fonts,
    wrap_text,
)
from .view import Cell, Grid
from .web_text_dialog import WebTextDialog, WebTextDialogError, is_web_runtime

_PANEL_PADDING = 18
_BUTTON_HEIGHT = 40
_BUTTON_SPACING = 9


class InputDialog:
    """Edit either puzzle using its data and semantic callbacks."""

    start_keys = (pygame.K_RETURN, pygame.K_KP_ENTER)

    def __init__(
        self,
        definition: PuzzleDefinition,
        initial_grid: object | None = None,
        initial_error: str | None = None,
    ) -> None:
        self.definition = definition
        self.title = f"{definition.title} · 문제 입력"
        self.prompt = definition.prompt
        self.json_description = "복사한 퍼즐 JSON을 붙여넣고 불러오기를 누르세요."
        self.draft = definition.normalize(
            initial_grid
            if initial_grid is not None
            else tuple(
                (definition.empty,) * definition.default_size
                for _ in range(definition.default_size)
            )
        )
        self._update_grid_layout(len(self.draft))
        self.dialog_width = self.layout.window_size[0]
        self.screen = configure_display(self.layout.window_size, self.title)
        self.fonts: Fonts = get_fonts(number_size=self.layout.number_font_size)
        self.preset_names = tuple(definition.presets)
        self.panel_x = self.layout.panel_rect.x
        self.panel_width = self.layout.panel_rect.width
        self.panel_inner_x = self.panel_x + _PANEL_PADDING
        self.panel_inner_width = self.panel_width - 2 * _PANEL_PADDING
        self.selected_cell: tuple[int, int] | None = None
        self.running = True
        self.quit_requested = False
        self.size_text = str(len(self.draft))
        self.size_focused = False
        self._replace_size_on_digit = False
        self._dragging = False
        self._drag_value: int | str | None = definition.empty
        self.selected_symbol: int | str | None = definition.empty
        self._symbol_selected = False
        self.validation_error = initial_error
        self.notice_message: str | None = None
        self._web_text_dialog: WebTextDialog | None = None
        self.editor_buttons: list[Button] = []
        self._init_buttons()

    def _update_grid_layout(self, board_size: int) -> None:
        self.layout = get_board_layout(board_size)
        if self.layout.stacked:
            columns = max(
                1,
                (self.layout.panel_rect.width - 36 + TOUCH_GAP)
                // (TOUCH_SIZE + TOUCH_GAP),
            )
            rows = (len(self.definition.symbols) + 1 + columns - 1) // columns
            self.layout = get_board_layout(
                board_size,
                panel_height=self.layout.panel_rect.height
                + 32
                + rows * (TOUCH_SIZE + TOUCH_GAP),
            )
        self.board_size = board_size
        self.cell_size = self.layout.cell_size
        self.grid_width = self.layout.board_rect.width
        self.grid_start_x, self.grid_start_y = self.layout.board_rect.topleft

    def _refresh_layout(self) -> bool:
        previous = self.layout
        self._update_grid_layout(self.board_size)
        if self.layout == previous:
            return False
        self.dialog_width = self.layout.window_size[0]
        self.screen = configure_display(self.layout.window_size, self.title)
        self.fonts = get_fonts(number_size=self.layout.number_font_size)
        self.panel_x = self.layout.panel_rect.x
        self.panel_width = self.layout.panel_rect.width
        self.panel_inner_x = self.panel_x + _PANEL_PADDING
        self.panel_inner_width = self.panel_width - 2 * _PANEL_PADDING
        self._dragging = False
        self._init_buttons()
        return True

    def _button(
        self, rect: pygame.Rect, label: str, *, primary: bool = False
    ) -> Button:
        if primary:
            return Button(rect, label, PRIMARY_DARK, self.fonts.button)
        return Button(
            rect,
            label,
            SURFACE_SUBTLE,
            self.fonts.button,
            text_color=PRIMARY_DARK,
            hover_color=SURFACE_HOVER,
            border_color=BORDER,
        )

    def _init_buttons(self) -> None:
        self.button_height = TOUCH_SIZE if self.layout.stacked else _BUTTON_HEIGHT
        gap = _BUTTON_SPACING
        columns = max(1, min(3, len(self.preset_names)))
        width = (self.panel_inner_width - (columns - 1) * gap) // columns
        self.preset_buttons = [
            self._button(
                pygame.Rect(
                    self.panel_inner_x + (index % columns) * (width + gap),
                    self.layout.panel_rect.top
                    + 42
                    + (index // columns) * (self.button_height + gap),
                    width,
                    self.button_height,
                ),
                name,
            )
            for index, name in enumerate(self.preset_names)
        ]
        preset_bottom = (
            self.preset_buttons[-1].rect.bottom
            if self.preset_buttons
            else self.layout.panel_rect.top + 42
        )
        action_y = self._init_editor_controls(preset_bottom + 18)
        self.symbol_buttons: list[tuple[int | str | None, Button]] = []
        if self.layout.stacked:
            self.symbol_heading_y = action_y
            action_y += 28
            columns = max(
                1, (self.panel_inner_width + TOUCH_GAP) // (TOUCH_SIZE + TOUCH_GAP)
            )
            width = (self.panel_inner_width - (columns - 1) * TOUCH_GAP) // columns
            for index, value in enumerate(
                (*self.definition.symbols, self.definition.empty)
            ):
                rect = pygame.Rect(
                    self.panel_inner_x + (index % columns) * (width + TOUCH_GAP),
                    action_y + (index // columns) * (TOUCH_SIZE + TOUCH_GAP),
                    width,
                    TOUCH_SIZE,
                )
                self.symbol_buttons.append(
                    (
                        value,
                        self._button(
                            rect,
                            "삭제" if value == self.definition.empty else str(value),
                        ),
                    )
                )
            action_y = self.symbol_buttons[-1][1].rect.bottom + 18
        width = (self.panel_inner_width - gap) // 2
        labels = (
            ("프롬프트 보기", "JSON 입력")
            if is_web_runtime()
            else ("프롬프트 복사", "JSON 붙여넣기")
        )
        self.copy_prompt_button, self.paste_button = [
            self._button(
                pygame.Rect(
                    self.panel_inner_x + index * (width + gap),
                    action_y,
                    width,
                    self.button_height,
                ),
                label,
            )
            for index, label in enumerate(labels)
        ]
        self.start_button = self._button(
            pygame.Rect(
                self.panel_inner_x,
                action_y + self.button_height + 18,
                self.panel_inner_width,
                self.button_height + 6,
            ),
            "풀이 시작",
            primary=True,
        )

    def _init_editor_controls(self, y: int) -> int:
        self.size_field_rect = pygame.Rect(
            self.panel_inner_x + 52, y, 58, self.button_height
        )
        variable_size = self.definition.size_range[0] != self.definition.size_range[1]
        x = self.size_field_rect.right + 9 if variable_size else self.panel_inner_x
        self.new_grid_button = self._button(
            pygame.Rect(
                x,
                y,
                self.panel_inner_x + self.panel_inner_width - x,
                self.button_height,
            ),
            "빈 격자 만들기",
        )
        self.editor_buttons = [self.new_grid_button]
        return y + self.button_height + 18

    def _show_error(self, message: str) -> None:
        self.validation_error = message
        self.notice_message = None

    def _show_notice(self, message: str) -> None:
        self.validation_error = None
        self.notice_message = message

    def _clear_message(self) -> None:
        self.validation_error = None
        self.notice_message = None

    def draw(self) -> None:
        self.screen.fill(APP_BACKGROUND)
        title = self.fonts.title.render(self.title, True, PRIMARY_DARK)
        self.screen.blit(title, title.get_rect(center=(self.dialog_width // 2, 35)))
        draw_panel(self.screen, self.layout.board_rect)
        draw_board(
            self.screen,
            self.layout,
            self.definition.editor_view(self.draft),
            self.fonts,
            selected_cell=self.selected_cell,
        )
        self._draw_panel()
        pygame.display.flip()

    def _draw_panel(self) -> None:
        draw_panel(
            self.screen,
            self.layout.panel_rect,
        )
        self.screen.blit(
            self.fonts.heading.render("예제 문제", True, BLACK),
            (self.panel_inner_x, self.layout.panel_rect.top + 14),
        )
        if self.progress_text:
            progress = self.fonts.info.render(self.progress_text, True, GRAY)
            self.screen.blit(
                progress,
                progress.get_rect(
                    topright=(
                        self.panel_inner_x + self.panel_inner_width,
                        self.layout.panel_rect.top + 19,
                    )
                ),
            )
        for button in (
            *self.preset_buttons,
            *self.editor_buttons,
            self.copy_prompt_button,
            self.paste_button,
            self.start_button,
        ):
            button.draw(self.screen)
        if self.symbol_buttons:
            self.screen.blit(
                self.fonts.info.render(
                    "입력할 값 · 선택 후 칸을 터치하세요", True, GRAY
                ),
                (self.panel_inner_x, self.symbol_heading_y),
            )
            for value, button in self.symbol_buttons:
                button.draw(self.screen)
                if self._symbol_selected and value == self.selected_symbol:
                    pygame.draw.rect(
                        self.screen, ACCENT, button.rect, width=3, border_radius=10
                    )
        self._draw_editor_controls()
        self._draw_instructions()
        self._draw_message()

    @property
    def progress_text(self) -> str:
        count = sum(
            value != self.definition.empty for row in self.draft for value in row
        )
        return f"입력 {count}/{self.board_size * self.board_size}"

    def _draw_editor_controls(self) -> None:
        if self.definition.size_range[0] == self.definition.size_range[1]:
            return
        label = self.fonts.info.render("크기 N", True, BLACK)
        self.screen.blit(
            label,
            label.get_rect(midleft=(self.panel_inner_x, self.size_field_rect.centery)),
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
        text = self.fonts.heading.render(self.size_text, True, BLACK)
        self.screen.blit(text, text.get_rect(center=self.size_field_rect.center))

    def _draw_instructions(self) -> None:
        y = self.start_button.rect.bottom + 24
        pygame.draw.line(
            self.screen,
            LIGHT_GRAY,
            (self.panel_inner_x, y - 10),
            (self.panel_inner_x + self.panel_inner_width, y - 10),
        )
        json_instruction = (
            "JSON 입력 창에 직접 붙여넣기"
            if is_web_runtime()
            else "JSON 버튼 또는 Ctrl+V로 붙여넣기"
        )
        for text in (
            f"{self.definition.symbols[0]}~{self.definition.symbols[-1]} 입력 · 0/Delete/Backspace 삭제",
            "화살표/Tab 이동 · 채운 칸에서 드래그",
            json_instruction,
            "Enter 시작 · Esc 퍼즐 선택",
        ):
            for line in wrap_text(f"• {text}", self.fonts.info, self.panel_inner_width):
                self.screen.blit(
                    self.fonts.info.render(line, True, GRAY),
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
        bottom = self.layout.panel_rect.bottom - 10
        for line in wrap_text(message, self.fonts.info, self.panel_inner_width):
            if y + self.fonts.info.get_linesize() > bottom:
                break
            self.screen.blit(
                self.fonts.info.render(line, True, color),
                (self.panel_inner_x, y),
            )
            y += 20

    def _handle_events(self, events: Iterable[pygame.event.Event]) -> Grid | None:
        events = tuple(events)
        # A close request wins even when Enter or a modal action was queued first.
        if any(event.type == pygame.QUIT for event in events):
            self.quit_requested = True
            self.running = False
            return None
        for event in events:
            if not self.running or self._web_text_dialog is not None:
                continue
            self._handle_editor_event(event)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                result = self._handle_mouse_click(event.pos)
                if result is not None:
                    return result
            elif event.type == pygame.KEYDOWN:
                result = self._handle_keydown(event)
                if result is not None:
                    return result
        return None

    def _handle_editor_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.WINDOWFOCUSLOST or (
            event.type == pygame.MOUSEBUTTONUP and event.button == 1
        ):
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            buttons = getattr(event, "buttons", ())
            if buttons and buttons[0]:
                cell = self.layout.cell_at(event.pos)
                if cell is not None:
                    self.selected_cell = cell
                    self._set_cell(cell, self._drag_value)

    def _handle_mouse_click(self, position: tuple[int, int]) -> Grid | None:
        if self._handle_editor_click(position):
            return None
        for index, button in enumerate(self.preset_buttons):
            if button.is_clicked(position):
                self._load_preset(index)
                return None
        if self.copy_prompt_button.is_clicked(position):
            self._handle_prompt_action()
        elif self.paste_button.is_clicked(position):
            self._handle_json_action()
        elif self.start_button.is_clicked(position):
            return self._handle_start()
        return None

    def _handle_editor_click(self, position: tuple[int, int]) -> bool:
        self.size_focused = False
        self._dragging = False
        for value, button in self.symbol_buttons:
            if button.is_clicked(position):
                self.selected_symbol = value
                self._symbol_selected = True
                if self.selected_cell is not None:
                    self._set_cell(self.selected_cell, value)
                return True
        if self.new_grid_button.is_clicked(position):
            self._apply_size()
            return True
        if self.definition.size_range[0] != self.definition.size_range[
            1
        ] and self.size_field_rect.collidepoint(position):
            self.size_focused = True
            self._replace_size_on_digit = True
            return True
        cell = self.layout.cell_at(position)
        if cell is not None:
            self.selected_cell = cell
            if self._symbol_selected:
                self._set_cell(cell, self.selected_symbol)
            self._drag_value = self.draft[cell[0]][cell[1]]
            self._dragging = self._drag_value != self.definition.empty
            return True
        return False

    def _handle_keydown(self, event: pygame.event.Event) -> Grid | None:
        if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
            self._handle_json_action()
        elif event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.mod & (pygame.KMOD_CTRL | pygame.KMOD_ALT | pygame.KMOD_GUI):
            return None
        elif not self._handle_editor_key(event) and event.key in self.start_keys:
            return self._handle_start()
        return None

    def _handle_editor_key(self, event: pygame.event.Event) -> bool:
        if self.size_focused:
            if event.key in self.start_keys:
                self._apply_size()
            elif event.key == pygame.K_TAB:
                self.size_focused = False
                self.selected_cell = self.selected_cell or (0, 0)
            elif event.key == pygame.K_BACKSPACE:
                self.size_text = (
                    "" if self._replace_size_on_digit else self.size_text[:-1]
                )
                self._replace_size_on_digit = False
            else:
                text = self._key_text(event)
                if len(text) == 1 and "0" <= text <= "9":
                    self.size_text = (
                        text if self._replace_size_on_digit else self.size_text + text
                    )[:2]
                    self._replace_size_on_digit = False
            return True
        if self._handle_grid_navigation(event):
            return True
        if self.selected_cell is None:
            return False
        if event.key in (pygame.K_DELETE, pygame.K_BACKSPACE, pygame.K_0, pygame.K_KP0):
            self._set_cell(self.selected_cell, self.definition.empty)
        else:
            text = self._key_text(event)
            for symbol in self.definition.symbols:
                if text == str(symbol):
                    self._set_cell(self.selected_cell, symbol)
                    break
        return False

    @staticmethod
    def _key_text(event: pygame.event.Event) -> str:
        keypad = (
            pygame.K_KP0,
            pygame.K_KP1,
            pygame.K_KP2,
            pygame.K_KP3,
            pygame.K_KP4,
            pygame.K_KP5,
            pygame.K_KP6,
            pygame.K_KP7,
            pygame.K_KP8,
            pygame.K_KP9,
        )
        if event.key in keypad:
            return str(keypad.index(event.key))
        if pygame.K_0 <= event.key <= pygame.K_9:
            return str(event.key - pygame.K_0)
        return getattr(event, "unicode", "").upper()

    def _set_cell(self, cell: Cell, value: int | str | None) -> None:
        row, column = cell
        if self.draft[row][column] == value:
            return
        rows = [list(row) for row in self.draft]
        rows[row][column] = value
        self.draft = self.definition.normalize(rows)
        save_draft(self.definition, self.draft)
        self._clear_message()

    def _replace_draft(self, grid: object, notice: str) -> None:
        draft: Grid = self.definition.normalize(grid)
        changed = draft != self.draft
        self.board_size = len(draft)
        self._refresh_layout()
        self.draft = draft
        self.selected_cell = None
        self.size_text = str(len(draft))
        self.size_focused = False
        self._replace_size_on_digit = False
        self._dragging = False
        self._drag_value = self.definition.empty
        if changed:
            save_draft(self.definition, self.draft)
        self._show_notice(notice)

    def _apply_size(self) -> None:
        low, high = self.definition.size_range
        if (
            not self.size_text.isascii()
            or not self.size_text.isdecimal()
            or len(self.size_text) > 2
            or not low <= int(self.size_text) <= high
        ):
            self._show_error(f"직접 입력 크기는 {low}~{high} 정수여야 합니다.")
            return
        size = int(self.size_text)
        self._replace_draft(
            tuple((self.definition.empty,) * size for _ in range(size)),
            f"빈 {size}×{size} 격자를 만들었습니다.",
        )

    def _load_preset(self, index: int) -> None:
        name = self.preset_names[index]
        self._replace_draft(
            self.definition.presets[name], f"{name} 문제를 불러왔습니다."
        )

    def _load_json_text(self, text: str) -> None:
        self._replace_draft(
            self.definition.parse(text),
            "JSON을 불러왔습니다. 원본 이미지와 확인하세요.",
        )

    def _handle_grid_navigation(self, event: pygame.event.Event) -> bool:
        if event.key == pygame.K_TAB:
            self._move_linear(-1 if event.mod & pygame.KMOD_SHIFT else 1)
            return True
        directions = {
            pygame.K_UP: (-1, 0),
            pygame.K_DOWN: (1, 0),
            pygame.K_LEFT: (0, -1),
            pygame.K_RIGHT: (0, 1),
        }
        direction = directions.get(event.key)
        if direction is None:
            return False
        self._move_direction(*direction)
        return True

    def _move_direction(self, row_offset: int, column_offset: int) -> None:
        if self.selected_cell is None:
            self.selected_cell = (0, 0)
            return
        size = self.board_size
        row, column = self.selected_cell
        self.selected_cell = (
            max(0, min(size - 1, row + row_offset)),
            max(0, min(size - 1, column + column_offset)),
        )

    def _move_linear(self, offset: int) -> None:
        if self.selected_cell is None:
            self.selected_cell = (0, 0)
            return
        row, column = self.selected_cell
        index = row * self.board_size + column
        target = max(0, min(self.board_size * self.board_size - 1, index + offset))
        self.selected_cell = divmod(target, self.board_size)

    def _handle_prompt_action(self) -> None:
        if is_web_runtime():
            self._open_web_dialog(
                lambda: WebTextDialog(
                    title="이미지 전사 프롬프트",
                    description="아래 텍스트를 선택한 뒤 브라우저의 시스템 복사를 사용하세요.",
                    text=self.prompt,
                    editable=False,
                )
            )
        else:
            self._copy_ai_prompt()

    def _copy_ai_prompt(self) -> None:
        try:
            copy_text(self.prompt)
        except ClipboardError as error:
            self._show_error(str(error))
            return
        self._show_notice("이미지 전사용 프롬프트를 복사했습니다.")

    def _handle_json_action(self) -> None:
        if is_web_runtime():
            self._open_web_dialog(
                lambda: WebTextDialog(
                    title="JSON 입력",
                    description=self.json_description,
                    text="",
                    editable=True,
                )
            )
        else:
            self._paste_json()

    def _paste_json(self) -> None:
        try:
            self._load_json_text(paste_text())
        except (ClipboardError, ValueError) as error:
            self._show_error(str(error))

    def _open_web_dialog(self, factory: Callable[[], WebTextDialog]) -> None:
        if self._web_text_dialog is not None:
            return
        self._dragging = False
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
                self._load_json_text(result.text)
            except ValueError as error:
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
        if dialog is not None:
            try:
                dialog.close()
            except WebTextDialogError as error:
                self._show_error(str(error))

    def _handle_start(self) -> Grid:
        self._clear_message()
        self.running = False
        return self.draft

    async def run(self) -> Grid | None:
        clock = pygame.time.Clock()
        try:
            self.draw()
            while self.running:
                await next_frame(clock)
                layout_changed = self._refresh_layout()
                events = pygame.event.get()
                result = self._handle_events(events)
                if result is not None:
                    return result
                dialog_changed = self.running and self._poll_web_text_dialog()
                if self.running and (events or dialog_changed or layout_changed):
                    self.draw()
            return None
        finally:
            self._close_web_text_dialog()

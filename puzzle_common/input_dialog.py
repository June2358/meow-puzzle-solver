"""One input screen with puzzle-specific drawing, editing and validation hooks."""

from collections.abc import Callable, Iterable

import pygame

from .clipboard import ClipboardError, copy_text, paste_text
from .layout import BOARD_AREA, GRID_START_Y, MARGIN, get_board_layout
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
    Fonts,
    configure_display,
    wrap_text,
)
from .web_text_dialog import WebTextDialog, WebTextDialogError, is_web_runtime

_PANEL_PADDING = 18
_BUTTON_HEIGHT = 40
_BUTTON_SPACING = 9


class InputDialog[PuzzleT]:
    """Own the input UI; subclasses supply the real puzzle rules and content."""

    title: str
    prompt: str
    json_description: str
    direct_instructions: tuple[str, ...]
    parse_error: type[Exception]
    start_keys = (pygame.K_RETURN, pygame.K_KP_ENTER)

    def __init__(
        self,
        fonts: Fonts,
        preset_names: tuple[str, ...],
        initial_error: str | None = None,
        *,
        board_size: int,
    ) -> None:
        self._update_grid_layout(board_size)
        self.dialog_width = self.layout.window_size[0]
        self.screen = configure_display(self.layout.window_size, self.title)
        self.fonts = fonts
        self.preset_names = preset_names
        self.panel_x = self.layout.panel_rect.x
        self.panel_width = self.layout.panel_rect.width
        self.panel_inner_x = self.panel_x + _PANEL_PADDING
        self.panel_inner_width = self.panel_width - 2 * _PANEL_PADDING
        self.selected_cell: tuple[int, int] | None = None
        self.running = True
        self.validation_error = initial_error
        self.notice_message: str | None = None
        self._web_text_dialog: WebTextDialog | None = None
        self.editor_buttons: list[Button] = []
        self._init_buttons()

    def _update_grid_layout(self, board_size: int) -> None:
        self.layout = get_board_layout(board_size)
        self.board_size = board_size
        self.cell_size = self.layout.cell_size
        self.grid_width = self.layout.board_rect.width
        self.grid_start_x, self.grid_start_y = self.layout.board_rect.topleft

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
        gap = _BUTTON_SPACING
        columns = min(3, len(self.preset_names))
        width = (self.panel_inner_width - (columns - 1) * gap) // columns
        self.preset_buttons = [
            self._button(
                pygame.Rect(
                    self.panel_inner_x + (index % columns) * (width + gap),
                    GRID_START_Y + 42 + (index // columns) * (_BUTTON_HEIGHT + gap),
                    width,
                    _BUTTON_HEIGHT,
                ),
                name,
            )
            for index, name in enumerate(self.preset_names)
        ]
        action_y = self._init_editor_controls(self.preset_buttons[-1].rect.bottom + 18)
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
                    _BUTTON_HEIGHT,
                ),
                label,
            )
            for index, label in enumerate(labels)
        ]
        self.start_button = self._button(
            pygame.Rect(
                self.panel_inner_x,
                action_y + _BUTTON_HEIGHT + 18,
                self.panel_inner_width,
                _BUTTON_HEIGHT + 6,
            ),
            "풀이 시작",
            primary=True,
        )

    def _init_editor_controls(self, y: int) -> int:
        return y

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
        draw_panel(
            self.screen, pygame.Rect(MARGIN, GRID_START_Y, BOARD_AREA, BOARD_AREA)
        )
        self._draw_grid()
        self._draw_panel()
        pygame.display.flip()

    def _draw_panel(self) -> None:
        draw_panel(
            self.screen,
            self.layout.panel_rect,
        )
        self.screen.blit(
            self.fonts.heading.render("예제 문제", True, BLACK),
            (self.panel_inner_x, GRID_START_Y + 14),
        )
        if self.progress_text:
            progress = self.fonts.info.render(self.progress_text, True, GRAY)
            self.screen.blit(
                progress,
                progress.get_rect(
                    topright=(
                        self.panel_inner_x + self.panel_inner_width,
                        GRID_START_Y + 19,
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
        self._draw_editor_controls()
        self._draw_instructions()
        self._draw_message()

    @property
    def progress_text(self) -> str:
        return ""

    def _draw_editor_controls(self) -> None:
        pass

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
            *self.direct_instructions,
            json_instruction,
            "Enter 시작 · Esc 종료",
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

    def _handle_events(self, events: Iterable[pygame.event.Event]) -> PuzzleT | None:
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
                return None
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
        pass

    def _handle_mouse_click(self, position: tuple[int, int]) -> PuzzleT | None:
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
        cell = self.layout.cell_at(position)
        if cell is not None:
            self.selected_cell = cell
        return False

    def _handle_keydown(self, event: pygame.event.Event) -> PuzzleT | None:
        if event.key == pygame.K_v and event.mod & pygame.KMOD_CTRL:
            self._handle_json_action()
        elif event.key == pygame.K_ESCAPE:
            self.running = False
        elif event.mod & (pygame.KMOD_CTRL | pygame.KMOD_ALT | pygame.KMOD_GUI):
            return None
        elif not self._handle_editor_key(event) and event.key in self.start_keys:
            return self._handle_start()
        return None

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
        except (ClipboardError, self.parse_error) as error:
            self._show_error(str(error))

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
                self._load_json_text(result.text)
            except self.parse_error as error:
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

    def _handle_start(self) -> PuzzleT | None:
        puzzle = self._create_puzzle()
        if puzzle is not None:
            self._clear_message()
            self.running = False
        return puzzle

    async def run(self) -> PuzzleT | None:
        clock = pygame.time.Clock()
        try:
            self.draw()
            while self.running:
                await next_frame(clock)
                events = pygame.event.get()
                result = self._handle_events(events)
                if result is not None:
                    return result
                dialog_changed = self.running and self._poll_web_text_dialog()
                if self.running and (events or dialog_changed):
                    self.draw()
            return None
        finally:
            self._close_web_text_dialog()

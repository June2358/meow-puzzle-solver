"""MEOW region editing and validation for the shared input screen."""

from typing import Final

import pygame

from puzzle_common.input_dialog import InputDialog
from puzzle_common.ui_style import (
    ACCENT,
    ACCENT_YELLOW,
    ACCENT_YELLOW_LIGHT,
    BLACK,
    BORDER,
    PRIMARY_DARK,
    SURFACE_SUBTLE,
    WHITE,
)

from .input_draft import IncompleteDraftError, RegionDraft
from .matrix_input import VISION_REGION_PROMPT
from .model import MAX_PUZZLE_SIZE, Cell, InvalidRegionMapError, Puzzle
from .parser import PuzzleParseError, parse_puzzle_json
from .puzzle_catalog import PRESET_NAMES, load_preset
from .ui_style import draw_region_grid_lines, get_fonts, region_palette

DEFAULT_DRAFT_SIZE: Final = 8
MIN_DIRECT_SIZE: Final = 1
MAX_DIRECT_SIZE: Final = MAX_PUZZLE_SIZE


class MeowInputDialog(InputDialog[Puzzle]):
    """Edit variable-size region labels; the common screen owns all UI flow."""

    title = "MEOW · Queens 문제 입력"
    prompt = VISION_REGION_PROMPT
    json_description = "복사한 N×N 영역 JSON을 아래 칸에 붙여넣고 불러오기를 누르세요."
    direct_instructions = (
        "A~Z 입력 · Delete/Backspace 삭제",
        "화살표/Tab 이동 · 채운 칸에서 드래그",
    )
    parse_error = PuzzleParseError

    def __init__(
        self,
        initial_grid: object | None = None,
        initial_error: str | None = None,
    ) -> None:
        self.draft = (
            RegionDraft.empty(DEFAULT_DRAFT_SIZE)
            if initial_grid is None
            else RegionDraft(initial_grid)
        )
        self.size_text = str(self.draft.size)
        self.size_focused = False
        self._replace_size_on_digit = False
        self._dragging = False
        self._drag_label: str | None = None
        super().__init__(
            get_fonts(), PRESET_NAMES, initial_error, board_size=self.draft.size
        )

    def _init_editor_controls(self, y: int) -> int:
        self._direct_title_y = y - 5
        self._image_title_y = y + 77
        self.size_field_rect = pygame.Rect(self.panel_inner_x + 52, y + 22, 58, 40)
        x = self.size_field_rect.right + 9
        self.new_grid_button = self._button(
            pygame.Rect(x, y + 22, self.panel_inner_x + self.panel_inner_width - x, 40),
            "빈 격자 만들기",
        )
        self.editor_buttons.append(self.new_grid_button)
        return y + 104

    @property
    def progress_text(self) -> str:
        return (
            f"입력 {self.draft.filled_count}/{self.draft.size * self.draft.size} · "
            f"영역 {len(self.draft.labels)}/{self.draft.size}"
        )

    def _draw_editor_controls(self) -> None:
        for label, y in (
            ("직접 입력", self._direct_title_y),
            ("이미지 / JSON", self._image_title_y),
        ):
            self.screen.blit(
                self.fonts.info.render(label, True, PRIMARY_DARK),
                (self.panel_inner_x, y),
            )
        size_label = self.fonts.info.render("크기 N", True, BLACK)
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
        size = self.fonts.heading.render(self.size_text, True, BLACK)
        self.screen.blit(size, size.get_rect(center=self.size_field_rect.center))

    def _handle_editor_event(self, event: pygame.event.Event) -> None:
        if (
            event.type == pygame.WINDOWFOCUSLOST
            or event.type == pygame.MOUSEBUTTONUP
            and event.button == 1
        ):
            self._dragging = False
        elif event.type == pygame.MOUSEMOTION and self._dragging:
            buttons = getattr(event, "buttons", (False, False, False))
            if buttons and buttons[0] and self._drag_label is not None:
                cell = self._cell_at(event.pos)
                if cell is not None:
                    self._set_cell(cell, self._drag_label, advance=False)

    def _handle_editor_click(self, position: tuple[int, int]) -> bool:
        self.size_focused = False
        self._dragging = False
        if self.new_grid_button.is_clicked(position):
            self._apply_size()
            return True
        if self.size_field_rect.collidepoint(position):
            self.size_focused = True
            self._replace_size_on_digit = True
            return True
        cell = self._cell_at(position)
        if cell is not None:
            self.selected_cell = cell
            self._drag_label = self.draft.label_at(cell)
            self._dragging = self._drag_label is not None
        return False

    def _handle_editor_key(self, event: pygame.event.Event) -> bool:
        if self.size_focused:
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._apply_size()
            elif event.key == pygame.K_TAB:
                self.size_focused = False
                self.selected_cell = self.selected_cell or (0, 0)
            else:
                self._handle_size_key(event)
            return True
        self._handle_grid_key(event)
        return False

    def _replace_draft(self, draft: RegionDraft, notice: str) -> None:
        """Atomically replace the visible draft with an already-valid value."""

        self.draft = draft
        self.selected_cell = None
        self.size_text = str(draft.size)
        self.size_focused = False
        self._replace_size_on_digit = False
        self._dragging = False
        self._drag_label = None
        self._update_grid_layout(draft.size)
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

    def _draw_grid(self) -> None:
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
        if not label.isascii():
            # shortcut: Unicode widths can shrink; use shaping-aware metrics if fitting is slow.
            content = label
            while content and font.size(content + "…")[0] > width:
                content = content[:-1]
            return content + "…" if content else ""
        low, high = 0, len(label)
        while low < high:
            middle = (low + high + 1) // 2
            if font.size(label[:middle] + "…")[0] <= width:
                low = middle
            else:
                high = middle - 1
        return label[:low] + "…" if low else ""

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
        if self._handle_grid_navigation(event):
            return
        if self.selected_cell is None:
            return
        if event.key in (pygame.K_DELETE, pygame.K_BACKSPACE):
            self._set_cell(self.selected_cell, None, advance=False)
            self._drag_label = None
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

    def _load_json_text(self, text: str) -> None:
        """Parse first, then atomically replace the draft with validated JSON."""

        puzzle = parse_puzzle_json(text)
        self._replace_draft(
            RegionDraft(puzzle.region_grid),
            f"{puzzle.size}×{puzzle.size} JSON을 불러왔습니다. 원본 이미지와 확인하세요.",
        )

    def _create_puzzle(self) -> Puzzle | None:
        empty = self.draft.first_empty()
        if empty is not None:
            self.selected_cell = empty
        try:
            puzzle = self.draft.to_puzzle()
        except (IncompleteDraftError, InvalidRegionMapError) as error:
            self._show_error(str(error))
            return None
        return puzzle

    def _load_preset(self, index: int) -> None:
        name = PRESET_NAMES[index]
        puzzle = load_preset(name)
        self._replace_draft(
            RegionDraft(puzzle.region_grid),
            f"{name} 문제를 불러왔습니다.",
        )

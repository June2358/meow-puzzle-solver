"""One concrete playback screen consumes puzzle display data."""

from collections.abc import Iterable

import pygame

from .board import draw_board
from .engine import Outcome, SolveResult
from .layout import TOUCH_SIZE, get_board_layout
from .presentation import PlaybackFrame, build_frames
from .puzzle import PuzzleDefinition
from .runtime import next_frame
from .ui_components import Button, draw_panel
from .ui_style import (
    ACCENT,
    ACCENT_LIGHT,
    APP_BACKGROUND,
    BLACK,
    GRAY,
    LIGHT_GRAY,
    ORANGE,
    ORANGE_LIGHT,
    PRIMARY,
    PRIMARY_DARK,
    RED,
    RED_LIGHT,
    Color,
    configure_display,
    get_fonts,
    wrap_text,
)
from .view import Grid, PlaybackDetails

_NAVIGATION_REPEAT_DELAY = 0.36
_NAVIGATION_REPEAT_INTERVAL = 0.08
_AUTOPLAY_INTERVAL = 0.9
type _NavigationSource = tuple[str, int]


def _pack_effect_items(
    items: tuple[str, ...], font: pygame.font.Font, max_width: int
) -> tuple[str, ...]:
    """Keep complete cell/value effects together while packing lines."""

    if max_width <= 0:
        raise ValueError("텍스트 너비는 양수여야 합니다.")
    lines: list[str] = []
    current = ""
    for item in items:
        candidate = f"{current}   {item}" if current else item
        if current and font.size(candidate)[0] > max_width:
            lines.append(current)
            current = item
        else:
            current = candidate
    if current:
        lines.append(current)
    return tuple(lines)


class PlaybackScreen:
    """Own presentation and playback controls without importing a puzzle type."""

    def __init__(
        self,
        definition: PuzzleDefinition,
        grid: Grid,
        result: SolveResult,
    ) -> None:
        if not isinstance(result, SolveResult):
            raise TypeError("풀이 결과는 SolveResult이어야 합니다.")
        self.definition = definition
        self.grid = grid
        self.result = result
        self._frames = build_frames(result)
        definition.validate_frames(grid, self.frames)
        board_size = len(grid)
        self._board_size = board_size
        self.layout = layout = get_board_layout(board_size)
        self.cell_size = layout.cell_size
        self.board_rect = layout.board_rect
        self.board_origin = self.board_rect.topleft
        self.panel_rect = layout.panel_rect
        self.fonts = get_fonts(number_size=layout.number_font_size)
        self.screen = configure_display(
            layout.window_size, f"{definition.title} · 풀이 과정"
        )
        self.current_step_index = 0
        self.running = True
        self.autoplay_enabled = False
        self.autoplay_timer = 0.0
        self._held_navigation_sources: dict[_NavigationSource, int] = {}
        self._active_navigation_source: _NavigationSource | None = None
        self._navigation_repeat_timer = 0.0
        self._navigation_repeat_started = False
        self.details_scroll = 0
        self.details_max_scroll = 0
        self.details_page_size = 1
        self._init_buttons()

    def _refresh_layout(self) -> bool:
        layout = get_board_layout(self._board_size)
        if layout == self.layout:
            return False
        self.layout = layout
        self.cell_size = layout.cell_size
        self.board_rect = layout.board_rect
        self.board_origin = self.board_rect.topleft
        self.panel_rect = layout.panel_rect
        self.screen = configure_display(
            layout.window_size, f"{self.definition.title} · 풀이 과정"
        )
        self.fonts = get_fonts(number_size=layout.number_font_size)
        self._clear_navigation_holds()
        self._init_buttons()
        return True

    def _init_buttons(self) -> None:
        x = self.panel_rect.left + 16
        width = self.panel_rect.width - 32
        third = (width - 16) // 3
        height = TOUCH_SIZE if self.layout.stacked else 38
        y = self.panel_rect.bottom - (2 * height + 36)
        self.previous_button, self.play_button, self.next_button = (
            Button(
                pygame.Rect(x + index * (third + 8), y, third, height),
                text,
                color,
                self.fonts.button,
            )
            for index, (text, color) in enumerate(
                (("이전", PRIMARY), ("재생", ACCENT), ("다음", PRIMARY))
            )
        )
        self.edit_button = Button(
            pygame.Rect(x, y + height + 12, width, height),
            "문제 입력으로 돌아가기",
            PRIMARY_DARK,
            self.fonts.button,
        )

    @property
    def frames(
        self,
    ) -> tuple[PlaybackFrame, ...]:
        return self._frames

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def current_frame(self) -> PlaybackFrame:
        return self.frames[self.current_step_index]

    @property
    def outcome(self) -> Outcome:
        return self.result.outcome

    def _draw_board(self, frame: PlaybackFrame) -> None:
        view = self.definition.frame_view(self.grid, frame)
        if view.source is not frame.snapshot or view.size != self._board_size:
            raise ValueError("보드 표시가 전달된 문제에 속하지 않습니다.")
        draw_board(self.screen, self.layout, view, self.fonts)

    def _presentation(self, frame: PlaybackFrame) -> PlaybackDetails:
        return self.definition.describe(self.grid, frame, self.result)

    def _status_badge(self) -> tuple[str, Color, Color]:
        if self.outcome is Outcome.MULTIPLE:
            return "복수해 · 가능한 해 중 하나 표시", ORANGE, ORANGE_LIGHT
        if self.outcome is Outcome.UNSOLVABLE:
            return "해 없음 · 유효한 배치 없음", RED, RED_LIGHT
        return "유일해", ACCENT, ACCENT_LIGHT

    def _coordinate_labels(self) -> tuple[tuple[str, pygame.Rect], ...]:
        labels = []
        last_column_right = last_row_bottom = -1
        for index in range(self._board_size):
            for text, center in (
                (
                    f"C{index + 1}",
                    (
                        self.layout.cell_rect((0, index)).centerx,
                        self.board_rect.top - 13,
                    ),
                ),
                (
                    f"R{index + 1}",
                    (
                        self.board_rect.left - 18,
                        self.layout.cell_rect((index, 0)).centery,
                    ),
                ),
            ):
                rect = pygame.Rect((0, 0), self.fonts.info.size(text))
                rect.center = center
                if text.startswith("C"):
                    if rect.left <= last_column_right + 3:
                        continue
                    last_column_right = rect.right
                else:
                    if rect.top <= last_row_bottom + 3:
                        continue
                    last_row_bottom = rect.bottom
                labels.append((text, rect))
        return tuple(labels)

    def _draw_coordinates(self) -> None:
        for text, rect in self._coordinate_labels():
            self.screen.blit(self.fonts.info.render(text, True, GRAY), rect)

    def draw(self) -> None:
        self.screen.fill(APP_BACKGROUND)
        pygame.draw.rect(
            self.screen, LIGHT_GRAY, self.board_rect.move(0, 4), border_radius=5
        )
        frame = self.current_frame
        self._draw_board(frame)
        self._draw_coordinates()
        self._draw_panel(frame)
        pygame.display.flip()

    def _draw_panel(self, frame: PlaybackFrame) -> None:
        draw_panel(self.screen, self.panel_rect)
        details = self._presentation(frame)
        x, y = self.panel_rect.left + 18, self.panel_rect.top + 18
        width = self.panel_rect.width - 36
        self.screen.blit(
            self.fonts.title.render("풀이 과정", True, PRIMARY_DARK), (x, y)
        )
        y += 38
        text, color, background = self._status_badge()
        surface = self.fonts.info.render(text, True, color)
        rect = surface.get_rect(topleft=(x, y)).inflate(18, 10)
        rect.topleft = (x, y)
        pygame.draw.rect(self.screen, background, rect, border_radius=8)
        self.screen.blit(surface, (x + 9, y + 5))
        y = rect.bottom + 12
        counter = f"{self.current_step_index + 1} / {self.frame_count} 단계"
        self.screen.blit(self.fonts.heading.render(counter, True, BLACK), (x, y))
        y += 30
        y = self._draw_wrapped(
            details.title,
            x,
            y,
            color=PRIMARY,
            font=self.fonts.heading,
            max_width=width,
            max_y=y + 50,
        )
        for text, color in details.annotations:
            y = self._draw_wrapped(
                text,
                x,
                y,
                color=color,
                font=self.fonts.info,
                max_width=width,
                max_y=y + 48,
            )
        y = self._draw_region_chips(details.region_colors, x, y)
        pygame.draw.line(
            self.screen,
            LIGHT_GRAY,
            (x, y + 4),
            (self.panel_rect.right - 18, y + 4),
        )
        y += 18
        bottom = self.previous_button.rect.top - 42
        details_bottom = bottom - (36 if details.assumption else 0)
        self._draw_details(
            details, pygame.Rect(x, y, width, max(1, details_bottom - y))
        )
        if details.assumption:
            self.screen.blit(
                self.fonts.body.render(
                    f"활성 가정 · {details.assumption}", True, ORANGE
                ),
                (x, bottom - 25),
            )
        self.play_button.text = "일시정지" if self.autoplay_enabled else "재생"
        for button in (
            self.previous_button,
            self.play_button,
            self.next_button,
            self.edit_button,
        ):
            button.draw(self.screen)
        for offset, text in (
            (-32, "←/→ · Home/End 이동"),
            (-14, "Space 재생 · Esc 편집"),
        ):
            surface = self.fonts.info.render(text, True, GRAY)
            self.screen.blit(
                surface,
                surface.get_rect(
                    center=(
                        self.panel_rect.centerx,
                        self.previous_button.rect.top + offset,
                    )
                ),
            )

    def _detail_rows(
        self, details: PlaybackDetails, width: int
    ) -> tuple[tuple[str, Color], ...]:
        rows = [
            (line, GRAY)
            for line in wrap_text(
                details.reason or details.title, self.fonts.body, width
            )
        ]
        for label, items in details.effects:
            rows.append((label, PRIMARY))
            rows.extend(
                (line, GRAY)
                for packed in _pack_effect_items(items, self.fonts.body, width)
                for line in wrap_text(packed, self.fonts.body, width)
            )
        return tuple(rows)

    def _draw_details(self, details: PlaybackDetails, area: pygame.Rect) -> None:
        self.details_up_button, self.details_down_button = (
            Button(
                pygame.Rect(
                    area.right - (2 - index) * (TOUCH_SIZE + 6),
                    area.top,
                    TOUCH_SIZE,
                    TOUCH_SIZE,
                ),
                text,
                PRIMARY,
                self.fonts.button,
            )
            for index, text in enumerate(("↑", "↓"))
        )
        self.details_rect = pygame.Rect(
            area.left,
            area.top + TOUCH_SIZE + 6,
            area.width,
            max(1, area.height - TOUCH_SIZE - 6),
        )
        rows = self._detail_rows(details, self.details_rect.width)
        line_height = self.fonts.body.get_linesize() + 2
        visible = max(1, self.details_rect.height // line_height)
        self.details_page_size = max(1, visible - 1)
        self.details_max_scroll = max(0, len(rows) - visible)
        self._scroll_details(0)
        label = "사유 · 결과"
        if self.details_max_scroll:
            label += f" {self.details_scroll + 1}/{len(rows)}줄"
        self.screen.blit(
            self.fonts.info.render(label, True, PRIMARY), (area.left, area.top + 12)
        )
        previous_clip = self.screen.get_clip()
        self.screen.set_clip(self.details_rect)
        for index, (text, color) in enumerate(
            rows[self.details_scroll : self.details_scroll + visible]
        ):
            self.screen.blit(
                self.fonts.body.render(text, True, color),
                (area.left, self.details_rect.top + index * line_height),
            )
        self.screen.set_clip(previous_clip)
        for button in (self.details_up_button, self.details_down_button):
            button.draw(self.screen)

    def _scroll_details(self, offset: int) -> None:
        self.details_scroll = max(
            0, min(self.details_max_scroll, self.details_scroll + offset)
        )

    def _draw_region_chips(self, colors: tuple[Color, ...], x: int, y: int) -> int:
        if not colors:
            return y
        y += 5
        label = self.fonts.info.render("관련 색상 영역", True, GRAY)
        self.screen.blit(label, (x, y + 1))
        chip_x = x + label.get_width() + 10
        chip_size = max(16, self.fonts.info.get_height() - 1)
        for color in colors:
            if chip_x + chip_size > self.panel_rect.right - 18:
                chip_x = x
                y += chip_size + 6
            rect = pygame.Rect(chip_x, y, chip_size, chip_size)
            pygame.draw.rect(self.screen, color, rect, border_radius=4)
            pygame.draw.rect(self.screen, BLACK, rect, width=2, border_radius=4)
            chip_x += chip_size + 6
        return y + max(label.get_height(), chip_size) + 8

    def _draw_lines(
        self,
        lines: tuple[str, ...],
        x: int,
        y: int,
        *,
        color: Color,
        font: pygame.font.Font,
        max_y: int,
    ) -> int:
        line_height = font.get_linesize() + 2
        available = max(0, (max_y - y) // line_height)
        if len(lines) > available:
            if not available:
                return y
            lines = (*lines[: available - 1], "…")
        for line in lines:
            self.screen.blit(font.render(line, True, color), (x, y))
            y += line_height
        return y

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
        font = font or self.fonts.body
        return self._draw_lines(
            wrap_text(text, font, max_width), x, y, color=color, font=font, max_y=max_y
        )

    def _navigate(self, offset: int) -> bool:
        target = max(0, min(self.frame_count - 1, self.current_step_index + offset))
        if target == self.current_step_index:
            return False
        self._set_index(target)
        return True

    def _set_index(self, index: int) -> None:
        self.current_step_index = max(0, min(self.frame_count - 1, index))
        self.autoplay_timer = 0.0
        self.details_scroll = 0

    def _toggle_autoplay(self) -> None:
        self._clear_navigation_holds()
        if self.current_step_index == self.frame_count - 1:
            self.current_step_index = 0
        self.autoplay_enabled = not self.autoplay_enabled
        self.autoplay_timer = 0.0

    def _begin_navigation_hold(self, source: _NavigationSource, offset: int) -> None:
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
        if self._active_navigation_source == source:
            self._active_navigation_source = next(
                reversed(self._held_navigation_sources), None
            )
            self._navigation_repeat_timer = 0.0
            self._navigation_repeat_started = False

    def _clear_navigation_holds(self) -> None:
        self._held_navigation_sources.clear()
        self._active_navigation_source = None
        self._navigation_repeat_timer = 0.0
        self._navigation_repeat_started = False

    def _update_navigation_hold(self, elapsed: float) -> bool:
        if self._active_navigation_source is None:
            return False
        offset = self._held_navigation_sources[self._active_navigation_source]
        self._navigation_repeat_timer += elapsed
        threshold = (
            _NAVIGATION_REPEAT_INTERVAL
            if self._navigation_repeat_started
            else _NAVIGATION_REPEAT_DELAY
        )
        changed = False
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
        changed = self._navigate(1)
        self.autoplay_timer = 0.0
        if self.current_step_index == self.frame_count - 1:
            self.autoplay_enabled = False
        return changed

    def _handle_keydown(self, event: pygame.event.Event) -> str | None:
        if event.key == pygame.K_ESCAPE:
            self._clear_navigation_holds()
            return "edit"
        if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
            self._begin_navigation_hold(
                ("key", event.key), -1 if event.key == pygame.K_LEFT else 1
            )
        elif event.key in (pygame.K_HOME, pygame.K_END):
            self._clear_navigation_holds()
            self.autoplay_enabled = False
            self._set_index(0 if event.key == pygame.K_HOME else self.frame_count - 1)
        elif event.key == pygame.K_SPACE:
            self._toggle_autoplay()
        elif event.key in (pygame.K_PAGEUP, pygame.K_PAGEDOWN):
            self._scroll_details(
                -self.details_page_size
                if event.key == pygame.K_PAGEUP
                else self.details_page_size
            )
        return None

    def _handle_mouse_down(self, event: pygame.event.Event) -> str | None:
        if event.button != 1:
            return None
        if hasattr(self, "details_up_button") and self.details_up_button.is_clicked(
            event.pos
        ):
            self._scroll_details(-1)
        elif hasattr(
            self, "details_down_button"
        ) and self.details_down_button.is_clicked(event.pos):
            self._scroll_details(1)
        elif self.previous_button.is_clicked(event.pos):
            self._begin_navigation_hold(("mouse", event.button), -1)
        elif self.play_button.is_clicked(event.pos):
            self._toggle_autoplay()
        elif self.next_button.is_clicked(event.pos):
            self._begin_navigation_hold(("mouse", event.button), 1)
        elif self.edit_button.is_clicked(event.pos):
            self._clear_navigation_holds()
            return "edit"
        return None

    def _handle_events(self, events: Iterable[pygame.event.Event]) -> str | None:
        events = tuple(events)
        if any(event.type == pygame.QUIT for event in events):
            self._clear_navigation_holds()
            self.running = False
            return None
        for event in events:
            if event.type == pygame.WINDOWFOCUSLOST:
                self._clear_navigation_holds()
            elif event.type == pygame.KEYDOWN:
                action = self._handle_keydown(event)
                if action is not None:
                    return action
            elif event.type == pygame.KEYUP:
                self._end_navigation_hold(("key", event.key))
            elif event.type == pygame.MOUSEBUTTONDOWN:
                action = self._handle_mouse_down(event)
                if action is not None:
                    return action
            elif event.type == pygame.MOUSEBUTTONUP:
                self._end_navigation_hold(("mouse", event.button))
            elif event.type == pygame.MOUSEWHEEL:
                self._scroll_details(-event.y * 3)
        return None

    async def run(self) -> bool:
        clock = pygame.time.Clock()
        self.draw()
        while self.running:
            elapsed = await next_frame(clock)
            layout_changed = self._refresh_layout()
            navigation_source = self._active_navigation_source
            autoplay_was_enabled = self.autoplay_enabled
            events = pygame.event.get()
            if self._handle_events(events) == "edit":
                return True
            if not self.running:
                break
            changed = bool(events) or layout_changed
            if (
                navigation_source is not None
                and navigation_source == self._active_navigation_source
            ):
                changed = self._update_navigation_hold(elapsed) or changed
            if autoplay_was_enabled:
                changed = self._update_autoplay(elapsed) or changed
            if changed:
                self.draw()
        return False

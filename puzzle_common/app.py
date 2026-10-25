"""Compose registered definitions into one selector/editor/player lifecycle."""

import sys
from urllib.parse import parse_qs

import pygame

from meow.definition import DEFINITION as MEOW
from sudoku.definition import DEFINITION as SUDOKU

from .drafts import load_drafts, save_draft
from .engine import Outcome
from .input_dialog import InputDialog
from .layout import get_board_layout
from .playback import PlaybackScreen
from .runtime import browser_viewport, browser_window, next_frame
from .ui_components import Button, draw_panel
from .ui_style import APP_BACKGROUND, PRIMARY_DARK, configure_display, get_fonts

DEFINITIONS = (MEOW, SUDOKU)
UNSOLVABLE_MESSAGE = (
    "현재 입력으로 가능한 해가 없습니다. 원본 문제와 입력을 확인하세요."
)


def _menu_size() -> tuple[int, int]:
    viewport = browser_viewport()
    width, height = get_board_layout(9).window_size
    return width, max(400, min(700, viewport[1])) if viewport else height


class PuzzleSelector:
    """Choose a registered puzzle with the mouse, arrows, Tab, or Enter."""

    def __init__(self) -> None:
        self.fonts = get_fonts()
        self.selected = 0
        self._resize()

    def _resize(self) -> None:
        self.screen = configure_display(_menu_size(), "퍼즐 솔버")
        width, height = self.screen.get_size()
        panel_width = min(480, width - 32)
        self.panel = pygame.Rect(
            (width - panel_width) // 2, height // 2 - 160, panel_width, 320
        )
        self.buttons = [
            Button(
                pygame.Rect(
                    self.panel.x + 24,
                    self.panel.y + 80 + index * 76,
                    panel_width - 48,
                    56,
                ),
                definition.title,
                PRIMARY_DARK,
                self.fonts.button,
            )
            for index, definition in enumerate(DEFINITIONS)
        ]

    def _handle_events(self, events) -> str | None:
        if any(event.type == pygame.QUIT for event in events):
            return "quit"
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and sys.platform != "emscripten":
                    return "quit"
                if event.key in (pygame.K_DOWN, pygame.K_RIGHT, pygame.K_TAB):
                    direction = -1 if event.mod & pygame.KMOD_SHIFT else 1
                    self.selected = (self.selected + direction) % len(self.buttons)
                elif event.key in (pygame.K_UP, pygame.K_LEFT):
                    self.selected = (self.selected - 1) % len(self.buttons)
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return DEFINITIONS[self.selected].key
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for definition, button in zip(DEFINITIONS, self.buttons, strict=True):
                    if button.is_clicked(event.pos):
                        return definition.key
        return None

    def draw(self) -> None:
        self.screen.fill(APP_BACKGROUND)
        draw_panel(self.screen, self.panel)
        title = self.fonts.title.render("퍼즐을 선택하세요", True, PRIMARY_DARK)
        self.screen.blit(
            title, title.get_rect(center=(self.panel.centerx, self.panel.y + 40))
        )
        for index, button in enumerate(self.buttons):
            button.draw(self.screen)
            if index == self.selected:
                pygame.draw.rect(
                    self.screen,
                    PRIMARY_DARK,
                    button.rect.inflate(8, 8),
                    2,
                    border_radius=12,
                )
        hint = self.fonts.info.render(
            "방향키 / Tab · Enter 선택"
            + (" · Esc 종료" if sys.platform != "emscripten" else ""),
            True,
            PRIMARY_DARK,
        )
        self.screen.blit(
            hint, hint.get_rect(center=(self.panel.centerx, self.panel.bottom - 30))
        )
        pygame.display.flip()

    async def run(self) -> str | None:
        clock = pygame.time.Clock()
        while True:
            if self.screen.get_size() != _menu_size():
                self._resize()
            action = self._handle_events(pygame.event.get())
            if action is not None:
                return None if action == "quit" else action
            self.draw()
            await next_frame(clock)


def _browser_initial_key() -> str | None:
    if sys.platform != "emscripten":
        return None
    key = parse_qs(str(browser_window().location.search).lstrip("?")).get(
        "puzzle", [None]
    )[0]
    return key if any(definition.key == key for definition in DEFINITIONS) else None


async def run_app(initial_key: str | None = None) -> None:
    definitions = {definition.key: definition for definition in DEFINITIONS}
    if initial_key is not None and initial_key not in definitions:
        raise ValueError(f"지원하지 않는 퍼즐입니다: {initial_key}")
    key = initial_key if initial_key is not None else _browser_initial_key()
    drafts = load_drafts(DEFINITIONS)
    error: str | None = None
    pygame.init()
    try:
        pygame.key.stop_text_input()
        while True:
            if key is None:
                key = await PuzzleSelector().run()
                if key is None:
                    return
            definition = definitions[key]
            if sys.platform == "emscripten":
                window = browser_window()
                url = window.URL.new(window.location.href)
                url.searchParams.set("puzzle", key)
                window.history.replaceState(window.history.state, "", url.href)
            editor = InputDialog(definition, drafts.get(key), error)
            grid = await editor.run()
            drafts[key] = editor.draft
            save_draft(definition, editor.draft)
            if editor.quit_requested:
                return
            if grid is None:
                error = None
                key = None
                continue
            try:
                result = definition.solve(grid)
            except ValueError as invalid:
                error = str(invalid)
                continue
            error = UNSOLVABLE_MESSAGE if result.outcome is Outcome.UNSOLVABLE else None
            if error is not None:
                continue
            if not await PlaybackScreen(definition, grid, result).run():
                return
    finally:
        pygame.quit()

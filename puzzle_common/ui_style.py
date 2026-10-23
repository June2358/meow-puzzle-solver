"""Shared pygame colors, fonts, display setup, and text wrapping."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pygame

type Color = tuple[int, int, int]

# Primary and accent colors are intentionally dark enough for compact Korean text.
PRIMARY = (37, 99, 235)
PRIMARY_DARK = (30, 64, 175)
PRIMARY_LIGHT = (191, 219, 254)

ACCENT = (21, 128, 61)
ACCENT_LIGHT = (187, 247, 208)
ACCENT_YELLOW = (250, 204, 21)
ACCENT_YELLOW_LIGHT = (254, 240, 138)

WHITE = (255, 255, 255)
APP_BACKGROUND = (246, 248, 252)
SURFACE_SUBTLE = (248, 250, 252)
SURFACE_HOVER = (239, 246, 255)
BLACK = (15, 23, 42)
GRAY = (71, 85, 105)
LIGHT_GRAY = (226, 232, 240)
BORDER = (203, 213, 225)
GRID_LINE = (148, 163, 184)
GRID_REGION_LINE = (30, 41, 59)
GRID_BOX_LINE = GRID_REGION_LINE
CANDIDATE_GRAY = (100, 116, 139)

RED = (220, 38, 38)
RED_LIGHT = (254, 202, 202)
ORANGE = (194, 65, 12)
ORANGE_LIGHT = (254, 215, 170)

_FONT_DIR = Path(__file__).parent / "assets" / "fonts"
_REGULAR_FONT_PATH = _FONT_DIR / "Pretendard-Regular.otf"
_SEMIBOLD_FONT_PATH = _FONT_DIR / "Pretendard-SemiBold.otf"


@dataclass(frozen=True, slots=True)
class Fonts:
    """Named font roles shared by the input and playback screens."""

    number: pygame.font.Font
    body: pygame.font.Font
    candidate: pygame.font.Font
    button: pygame.font.Font
    heading: pygame.font.Font
    title: pygame.font.Font
    info: pygame.font.Font


def _load_bundled_font(path: Path, size: int) -> pygame.font.Font:
    """Load one exact bundled Pretendard weight."""

    return pygame.font.Font(str(path), size)


def get_fonts(*, number_size: int, candidate_size: int) -> Fonts:
    """Create deterministic font roles shared by Desktop and Web."""

    if not pygame.font.get_init():
        pygame.font.init()
    return Fonts(
        number=_load_bundled_font(_SEMIBOLD_FONT_PATH, number_size),
        body=_load_bundled_font(_REGULAR_FONT_PATH, 17),
        candidate=_load_bundled_font(_REGULAR_FONT_PATH, candidate_size),
        button=_load_bundled_font(_SEMIBOLD_FONT_PATH, 17),
        heading=_load_bundled_font(_SEMIBOLD_FONT_PATH, 19),
        title=_load_bundled_font(_SEMIBOLD_FONT_PATH, 25),
        info=_load_bundled_font(_REGULAR_FONT_PATH, 15),
    )


def configure_display(size: tuple[int, int], caption: str) -> pygame.Surface:
    """Reuse the display surface and resize it only when the screen requires it."""

    screen = pygame.display.get_surface()
    if screen is None or screen.get_size() != size:
        screen = pygame.display.set_mode(size)
    pygame.display.set_caption(caption)
    return screen


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> tuple[str, ...]:
    """Wrap by rendered width, including Korean text without spaces."""

    if max_width <= 0:
        raise ValueError("텍스트 너비는 양수여야 합니다.")

    lines: list[str] = []
    for paragraph in text.splitlines() or [""]:
        current = ""
        for character in paragraph:
            candidate = current + character
            if current and font.size(candidate)[0] > max_width:
                lines.append(current.rstrip())
                current = character.lstrip()
            else:
                current = candidate
        lines.append(current.rstrip())
    return tuple(lines)


def draw_grid_lines(
    screen: pygame.Surface,
    origin: tuple[int, int],
    cell_size: int,
    size: int,
    *,
    color: Color,
    width: int,
) -> None:
    start_x, start_y = origin
    board_size = size * cell_size
    for index in range(size + 1):
        x = start_x + index * cell_size
        y = start_y + index * cell_size
        pygame.draw.line(screen, color, (x, start_y), (x, start_y + board_size), width)
        pygame.draw.line(screen, color, (start_x, y), (start_x + board_size, y), width)

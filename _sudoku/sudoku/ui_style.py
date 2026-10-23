"""Shared pygame colors, fonts, layouts, and Sudoku drawing helpers."""

from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path

import pygame

from .topology import BOX_SIZE, SIZE, Cell

# 주조색 (Primary) - 작은 글씨에서도 번지지 않는 파란색
PRIMARY = (37, 99, 235)  # #2563EB
PRIMARY_DARK = (30, 64, 175)  # #1E40AF
PRIMARY_LIGHT = (191, 219, 254)  # #BFDBFE

# 강조색 (Accent) - 부드러운 녹색/노란색
ACCENT = (21, 128, 61)  # #15803D
ACCENT_YELLOW = (250, 204, 21)  # #FACC15 - 부드러운 노란색
ACCENT_YELLOW_LIGHT = (254, 240, 138)  # #FEF08A - 연한 노란색

# 기본 색상
WHITE = (255, 255, 255)
APP_BACKGROUND = (246, 248, 252)  # #F6F8FC
SURFACE_SUBTLE = (248, 250, 252)  # #F8FAFC
SURFACE_HOVER = (239, 246, 255)  # #EFF6FF
BLACK = (15, 23, 42)  # #0F172A
GRAY = (71, 85, 105)  # #475569
LIGHT_GRAY = (226, 232, 240)  # #E2E8F0
BORDER = (203, 213, 225)  # #CBD5E1
GRID_LINE = (148, 163, 184)  # #94A3B8
GRID_BOX_LINE = (30, 41, 59)  # #1E293B
CANDIDATE_GRAY = (100, 116, 139)  # #64748B

# 기능 색상
RED = (220, 38, 38)  # #DC2626
ORANGE = (194, 65, 12)  # #C2410C

_FONT_DIR = Path(__file__).parent / "assets" / "fonts"
_REGULAR_FONT_PATH = _FONT_DIR / "Pretendard-Regular.otf"
_SEMIBOLD_FONT_PATH = _FONT_DIR / "Pretendard-SemiBold.otf"


@dataclass(frozen=True, slots=True)
class Fonts:
    """Named font roles shared by both pygame screens."""

    number: pygame.font.Font
    body: pygame.font.Font
    candidate: pygame.font.Font
    button: pygame.font.Font
    heading: pygame.font.Font
    title: pygame.font.Font


def _load_bundled_font(path: Path, size: int) -> pygame.font.Font:
    """Load one exact bundled Pretendard weight."""

    return pygame.font.Font(str(path), size)


def get_fonts() -> Fonts:
    """Create deterministic font roles shared by Desktop and Web."""

    if not pygame.font.get_init():
        pygame.font.init()
    return Fonts(
        number=_load_bundled_font(_SEMIBOLD_FONT_PATH, 38),
        body=_load_bundled_font(_REGULAR_FONT_PATH, 17),
        candidate=_load_bundled_font(_REGULAR_FONT_PATH, 15),
        button=_load_bundled_font(_SEMIBOLD_FONT_PATH, 17),
        heading=_load_bundled_font(_SEMIBOLD_FONT_PATH, 19),
        title=_load_bundled_font(_SEMIBOLD_FONT_PATH, 25),
    )


def configure_display(size: tuple[int, int], caption: str) -> pygame.Surface:
    """Return the current display surface, resizing it only when required."""

    screen = pygame.display.get_surface()
    if screen is None or screen.get_size() != size:
        screen = pygame.display.set_mode(size)
    pygame.display.set_caption(caption)
    return screen


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> tuple[str, ...]:
    """Wrap text by rendered pixel width, including Korean without spaces."""

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


# ============================================================================
# 공통 그리드/모순 셀 그리기 유틸
# ============================================================================


def draw_sudoku_grid_lines(
    screen: pygame.Surface,
    origin: tuple[int, int],
    cell_size: int,
    *,
    thick_width: int = 3,
    thin_width: int = 1,
) -> None:
    """Draw a 9x9 grid with heavier box boundaries."""

    start_x, start_y = origin
    for i in range(SIZE + 1):
        is_box_line = i % BOX_SIZE == 0
        line_width = thick_width if is_box_line else thin_width
        color = GRID_BOX_LINE if is_box_line else GRID_LINE

        # 세로선
        x = start_x + i * cell_size
        pygame.draw.line(
            screen,
            color,
            (x, start_y),
            (x, start_y + SIZE * cell_size),
            line_width,
        )

        # 가로선
        y = start_y + i * cell_size
        pygame.draw.line(
            screen,
            color,
            (start_x, y),
            (start_x + SIZE * cell_size, y),
            line_width,
        )


def draw_conflict_cells(
    screen: pygame.Surface,
    conflicts: Collection[Cell],
    origin: tuple[int, int],
    cell_size: int,
    *,
    alpha: int = 128,
) -> None:
    """Fill every conflicting cell with translucent red."""

    if not conflicts:
        return

    start_x, start_y = origin
    cell_surface = pygame.Surface((cell_size - 2, cell_size - 2))
    cell_surface.set_alpha(alpha)
    cell_surface.fill(RED)

    for row, col in conflicts:
        x = start_x + col * cell_size
        y = start_y + row * cell_size
        screen.blit(cell_surface, (x + 1, y + 1))

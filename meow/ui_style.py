"""공유 pygame 색상·폰트와 영역 보드 그리기 도우미."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass
from functools import cache
from pathlib import Path

import pygame

from .model import RegionGrid

type Color = tuple[int, int, int]

# 작은 한글도 읽기 쉽도록 기본색과 강조색을 충분히 어둡게 둔다.
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

RED = (220, 38, 38)
RED_LIGHT = (254, 202, 202)
ORANGE = (194, 65, 12)
ORANGE_LIGHT = (254, 215, 170)

_FONT_DIR = Path(__file__).parent / "assets" / "fonts"
_REGULAR_FONT_PATH = _FONT_DIR / "Pretendard-Regular.otf"
_SEMIBOLD_FONT_PATH = _FONT_DIR / "Pretendard-SemiBold.otf"


@dataclass(frozen=True, slots=True)
class Fonts:
    """입력 화면과 재생 화면이 공유하는 이름별 폰트 역할."""

    number: pygame.font.Font
    body: pygame.font.Font
    candidate: pygame.font.Font
    button: pygame.font.Font
    heading: pygame.font.Font
    title: pygame.font.Font


def get_fonts() -> Fonts:
    """데스크톱과 웹이 공유하는 고정된 폰트 역할을 만든다."""

    if not pygame.font.get_init():
        pygame.font.init()
    return Fonts(
        number=pygame.font.Font(_SEMIBOLD_FONT_PATH, 34),
        body=pygame.font.Font(_REGULAR_FONT_PATH, 17),
        candidate=pygame.font.Font(_REGULAR_FONT_PATH, 13),
        button=pygame.font.Font(_SEMIBOLD_FONT_PATH, 17),
        heading=pygame.font.Font(_SEMIBOLD_FONT_PATH, 19),
        title=pygame.font.Font(_SEMIBOLD_FONT_PATH, 25),
    )


def configure_display(size: tuple[int, int], caption: str) -> pygame.Surface:
    """화면 surface를 재사용하고 화면에 필요할 때만 크기를 바꾼다."""

    screen = pygame.display.get_surface()
    if screen is None or screen.get_size() != size:
        screen = pygame.display.set_mode(size)
    pygame.display.set_caption(caption)
    return screen


def wrap_text(text: str, font: pygame.font.Font, max_width: int) -> tuple[str, ...]:
    """공백 없는 한글도 렌더링 너비에 맞춰 줄바꿈한다."""

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


@cache
def region_palette(labels: tuple[str, ...]) -> dict[str, Color]:
    """주어진 영역 수에 맞는 고정된 서로 다른 파스텔 색상을 반환한다."""

    palette: dict[str, Color] = {}
    for index, label in enumerate(labels):
        hue = ((index * 137.508) + 8.0) % 360.0
        saturation = 0.25 + (index % 3) * 0.035
        value = 0.97 - (index % 2) * 0.025
        red, green, blue = colorsys.hsv_to_rgb(hue / 360.0, saturation, value)
        palette[label] = (
            round(red * 255),
            round(green * 255),
            round(blue * 255),
        )
    return palette


def draw_region_grid_lines(
    screen: pygame.Surface,
    region_grid: RegionGrid,
    origin: tuple[int, int],
    cell_size: int,
    *,
    region_width: int = 3,
    cell_width: int = 1,
) -> None:
    """얇은 칸 선과 색상 영역 사이의 굵은 경계를 그린다."""

    if cell_size <= 0:
        raise ValueError("셀 크기는 양수여야 합니다.")
    size = len(region_grid)
    start_x, start_y = origin
    board_size = size * cell_size

    for index in range(size + 1):
        x = start_x + index * cell_size
        y = start_y + index * cell_size
        pygame.draw.line(
            screen,
            GRID_LINE,
            (x, start_y),
            (x, start_y + board_size),
            cell_width,
        )
        pygame.draw.line(
            screen,
            GRID_LINE,
            (start_x, y),
            (start_x + board_size, y),
            cell_width,
        )

    for row in range(size):
        y1 = start_y + row * cell_size
        y2 = y1 + cell_size
        for boundary in range(size + 1):
            if (
                boundary in (0, size)
                or region_grid[row][boundary - 1] != region_grid[row][boundary]
            ):
                x = start_x + boundary * cell_size
                pygame.draw.line(
                    screen,
                    GRID_REGION_LINE,
                    (x, y1),
                    (x, y2),
                    region_width,
                )

    for column in range(size):
        x1 = start_x + column * cell_size
        x2 = x1 + cell_size
        for boundary in range(size + 1):
            if (
                boundary in (0, size)
                or region_grid[boundary - 1][column] != region_grid[boundary][column]
            ):
                y = start_y + boundary * cell_size
                pygame.draw.line(
                    screen,
                    GRID_REGION_LINE,
                    (x1, y),
                    (x2, y),
                    region_width,
                )

import ast
from pathlib import Path

import pygame
import pytest

from puzzle_common import ui_style as shared_style


def _glyph_signature(
    font: pygame.font.Font, character: str
) -> tuple[tuple[int, int], bytes]:
    surface = font.render(character, True, "white")
    return surface.get_size(), pygame.image.tobytes(surface, "RGBA")


def _source_characters() -> tuple[str, ...]:
    root = Path(__file__).resolve().parents[2]
    texts: list[str] = []
    for path in (root / name for name in ("meow", "sudoku", "puzzle_common")):
        for source_file in path.rglob("*.py"):
            tree = ast.parse(
                source_file.read_text(encoding="utf-8-sig"), filename=str(source_file)
            )
            texts.extend(
                node.value
                for node in ast.walk(tree)
                if isinstance(node, ast.Constant) and isinstance(node.value, str)
            )
    return tuple(
        sorted(
            {
                character
                for text in texts
                for character in text
                if not character.isspace() and character != "\ufeff"
            }
        )
    )


@pytest.mark.parametrize(
    "font_path",
    (shared_style._REGULAR_FONT_PATH, shared_style._SEMIBOLD_FONT_PATH),
)
def test_bundled_fonts_render_every_source_character(font_path: Path) -> None:
    pygame.font.init()
    assert font_path.is_file()

    font = pygame.font.Font(str(font_path), 20)
    missing_glyph = _glyph_signature(font, "\U0010ffff")
    missing = [
        character
        for character in _source_characters()
        if _glyph_signature(font, character) == missing_glyph
    ]

    assert missing == []

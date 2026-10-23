import ast
from pathlib import Path

import pygame
import pytest

from sudoku import ui_style


def _glyph_signature(
    font: pygame.font.Font, character: str
) -> tuple[tuple[int, int], bytes]:
    surface = font.render(character, True, "white")
    return surface.get_size(), pygame.image.tobytes(surface, "RGBA")


def _source_characters() -> tuple[str, ...]:
    package = Path(ui_style.__file__).parent
    texts: list[str] = []
    for path in package.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8-sig"), filename=str(path))
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
    (ui_style._REGULAR_FONT_PATH, ui_style._SEMIBOLD_FONT_PATH),
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


def test_get_fonts_use_real_pretendard_weights() -> None:
    fonts = ui_style.get_fonts()
    all_fonts = (
        fonts.number,
        fonts.body,
        fonts.candidate,
        fonts.button,
        fonts.heading,
        fonts.title,
    )

    assert {font.name for font in all_fonts} == {"Pretendard"}
    assert fonts.body.style_name == "Regular"
    assert fonts.candidate.style_name == "Regular"
    assert fonts.number.style_name == "SemiBold"
    assert fonts.button.style_name == "SemiBold"
    assert fonts.heading.style_name == "SemiBold"
    assert fonts.title.style_name == "SemiBold"
    assert not any(font.get_bold() for font in all_fonts)
    assert fonts.candidate.get_point_size() == 15


def test_get_fonts_fails_when_a_bundled_asset_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(ui_style, "_REGULAR_FONT_PATH", tmp_path / "missing.otf")

    with pytest.raises((FileNotFoundError, pygame.error)):
        ui_style.get_fonts()

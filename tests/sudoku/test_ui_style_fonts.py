from pathlib import Path

import pygame
import pytest

from puzzle_common import ui_style
from puzzle_common import ui_style as shared_style


def test_get_fonts_use_real_pretendard_weights() -> None:
    fonts = ui_style.get_fonts()
    all_fonts = (
        fonts.number,
        fonts.body,
        fonts.candidate,
        fonts.button,
        fonts.heading,
        fonts.title,
        fonts.info,
    )

    assert {font.name for font in all_fonts} == {"Pretendard"}
    assert fonts.body.style_name == "Regular"
    assert fonts.info.style_name == "Regular"
    assert fonts.candidate.style_name == "Regular"
    assert fonts.number.style_name == "SemiBold"
    assert fonts.button.style_name == "SemiBold"
    assert fonts.heading.style_name == "SemiBold"
    assert fonts.title.style_name == "SemiBold"
    assert not any(font.get_bold() for font in all_fonts)
    assert fonts.candidate.get_point_size() == 13
    assert fonts.info.get_point_size() == 15


def test_get_fonts_fails_when_a_bundled_asset_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(shared_style, "_REGULAR_FONT_PATH", tmp_path / "missing.otf")

    with pytest.raises((FileNotFoundError, pygame.error)):
        ui_style.get_fonts()

"""Unicode clipboard access through pygame-ce."""

import pygame


class ClipboardError(RuntimeError):
    """Raised when the operating-system clipboard cannot be accessed."""


def _ensure_clipboard() -> None:
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        raise ClipboardError("화면이 준비되지 않아 클립보드를 사용할 수 없습니다.")


def copy_text(text: str) -> None:
    """Copy one Unicode string through pygame-ce's text clipboard API."""

    if not isinstance(text, str):
        raise TypeError("클립보드에 복사할 값은 문자열이어야 합니다.")
    _ensure_clipboard()
    try:
        pygame.scrap.put_text(text)
    except pygame.error as error:
        raise ClipboardError("클립보드에 텍스트를 복사할 수 없습니다.") from error


def paste_text() -> str:
    """Read one Unicode JSON document from the clipboard."""

    _ensure_clipboard()
    try:
        text = pygame.scrap.get_text()
    except pygame.error as error:
        raise ClipboardError("클립보드에서 텍스트를 읽을 수 없습니다.") from error
    if not text:
        raise ClipboardError("클립보드에 붙여넣을 텍스트가 없습니다.")
    return text.removeprefix("\ufeff")

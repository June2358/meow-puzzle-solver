"""External vision transcription contract and pygame-ce clipboard access."""

import pygame

VISION_REGION_PROMPT = """Transcribe the colored-region Queens puzzle in the attached image.

Rules:
1. Infer N from the visible square board and return exactly N rows of N cells.
2. Identify only the colored or bounded region containing each board cell.
3. Give every cell in the same region the same string label.
4. Name regions A, B, C, ... in first-seen order while scanning rows from
   left to right and top to bottom. The maximum supported size is 26×26.
5. Ignore cats, queens, crowns, X marks, hints, highlights, scores, buttons,
   text, and every other UI element outside or over the board.
6. Do not solve the puzzle, infer cat positions, or alter a region boundary.
7. Return raw JSON only: no explanation and no Markdown code fence.
8. Return an object containing exactly one field named "regions". Do not add
   size, name, source, solution, cats, excluded, or any other field.

Required shape example (format only; do not copy it unless it matches the image):
{"regions":[["A","A","B"],["C","B","B"],["C","C","B"]]}"""


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

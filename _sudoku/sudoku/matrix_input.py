"""External AI/OCR matrix contract and isolated clipboard access."""

import pygame

OCR_MATRIX_PROMPT = """Transcribe the Sudoku puzzle in the attached image.

Rules:
1. Do not solve the puzzle or infer any missing digit.
2. Read cells from top to bottom and left to right.
3. Copy only clearly visible fixed/given digits.
4. Use 0 for every blank or unreadable cell.
5. Ignore pencil marks, candidate notes, highlights, and surrounding text.
6. Return exactly one 9x9 JSON array of integers from 0 to 9.
7. Return raw JSON only: no explanation, Markdown code fence, or object wrapper.

The following example demonstrates the output format only. Do not copy its
digits unless they are actually visible in the attached image.

Example visible grid:
53..7....
6..195...
.98....6.
8...6...3
4..8.3..1
7...2...6
.6....28.
...419..5
....8..79

Required example output:
[
  [5, 3, 0, 0, 7, 0, 0, 0, 0],
  [6, 0, 0, 1, 9, 5, 0, 0, 0],
  [0, 9, 8, 0, 0, 0, 0, 6, 0],
  [8, 0, 0, 0, 6, 0, 0, 0, 3],
  [4, 0, 0, 8, 0, 3, 0, 0, 1],
  [7, 0, 0, 0, 2, 0, 0, 0, 6],
  [0, 6, 0, 0, 0, 0, 2, 8, 0],
  [0, 0, 0, 4, 1, 9, 0, 0, 5],
  [0, 0, 0, 0, 8, 0, 0, 7, 9]
]"""


class ClipboardError(RuntimeError):
    """Raised when the operating-system clipboard cannot be accessed."""


def _ensure_clipboard() -> None:
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        raise ClipboardError("화면이 준비되지 않아 클립보드를 사용할 수 없습니다.")


def copy_text(text: str) -> None:
    """Copy text through pygame-ce's string clipboard API."""

    if not isinstance(text, str):
        raise TypeError("클립보드에 복사할 값은 문자열이어야 합니다.")
    _ensure_clipboard()
    try:
        pygame.scrap.put_text(text)
    except pygame.error as exc:
        raise ClipboardError("클립보드에 텍스트를 복사할 수 없습니다.") from exc


def paste_text() -> str:
    """Read JSON text from the clipboard."""

    _ensure_clipboard()
    try:
        text = pygame.scrap.get_text()
    except pygame.error as exc:
        raise ClipboardError("클립보드에서 텍스트를 읽을 수 없습니다.") from exc

    if not text:
        raise ClipboardError("클립보드에 붙여넣을 텍스트가 없습니다.")
    return text.removeprefix("\ufeff")

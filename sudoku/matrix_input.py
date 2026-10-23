"""외부 AI/OCR 행렬 계약과 독립적인 클립보드 접근."""

import pygame

OCR_MATRIX_PROMPT = """첨부 이미지의 스도쿠 퍼즐을 전사하세요.

규칙:
1. 퍼즐을 풀거나 누락된 숫자를 추론하지 마세요.
2. 위에서 아래, 왼쪽에서 오른쪽 순서로 칸을 읽으세요.
3. 명확히 보이는 고정 단서 숫자만 옮기세요.
4. 빈칸이나 읽을 수 없는 칸은 0으로 표시하세요.
5. 연필 표시, 후보 메모, 강조와 주변 텍스트는 무시하세요.
6. 0~9 정수로 구성된 9×9 JSON 배열 하나만 반환하세요.
7. 설명, Markdown 코드 펜스, 객체 래퍼 없이 원시 JSON만 반환하세요.

아래 예시는 출력 형식만 보여 줍니다. 첨부 이미지에 실제로 보이는 숫자가
아니라면 예시의 숫자를 복사하지 마세요.

예시 입력 격자:
53..7....
6..195...
.98....6.
8...6...3
4..8.3..1
7...2...6
.6....28.
...419..5
....8..79

예시의 올바른 출력:
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
    """운영체제 클립보드에 접근할 수 없을 때 발생한다."""


def _ensure_clipboard() -> None:
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        raise ClipboardError("화면이 준비되지 않아 클립보드를 사용할 수 없습니다.")


def copy_text(text: str) -> None:
    """pygame-ce 문자열 클립보드 API로 텍스트를 복사한다."""

    if not isinstance(text, str):
        raise TypeError("클립보드에 복사할 값은 문자열이어야 합니다.")
    _ensure_clipboard()
    try:
        pygame.scrap.put_text(text)
    except pygame.error as exc:
        raise ClipboardError("클립보드에 텍스트를 복사할 수 없습니다.") from exc


def paste_text() -> str:
    """클립보드에서 JSON 텍스트를 읽는다."""

    _ensure_clipboard()
    try:
        text = pygame.scrap.get_text()
    except pygame.error as exc:
        raise ClipboardError("클립보드에서 텍스트를 읽을 수 없습니다.") from exc

    if not text:
        raise ClipboardError("클립보드에 붙여넣을 텍스트가 없습니다.")
    return text.removeprefix("\ufeff")

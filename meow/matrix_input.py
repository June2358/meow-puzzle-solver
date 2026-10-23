"""외부 비전 전사 계약과 pygame-ce 클립보드 접근."""

import pygame

VISION_REGION_PROMPT = """첨부 이미지의 색상 영역 Queens (1-star Star Battle) 퍼즐을 전사하세요.

규칙:
1. 정사각형 보드에서 N을 판별하고, 각 행이 N칸인 정확히 N개 행을 반환하세요.
2. 각 칸의 색상이나 경계로 구분되는 영역만 식별하세요.
3. 같은 영역의 모든 칸에 동일한 문자열 이름을 사용하세요.
4. 위에서 아래로, 각 행은 왼쪽에서 오른쪽으로 읽으며 처음 만나는 영역부터
   A, B, C, ...로 이름을 붙이세요. 최대 지원 크기는 26×26입니다.
5. 고양이, 퀸, 왕관, X 표시, 힌트, 강조, 점수, 버튼, 텍스트 등 보드 위나
   바깥에 겹친 UI 요소는 무시하세요.
6. 퍼즐을 풀거나 고양이 위치를 추론하거나 영역 경계를 바꾸지 마세요.
7. 설명이나 Markdown 코드 블록 없이 JSON만 반환하세요.
8. "regions" 필드 하나만 포함한 객체를 반환하세요. size, name, source,
   solution, cats, excluded 등 다른 필드는 추가하지 마세요.

필수 형식 예시 (이미지와 일치할 때만 값을 그대로 사용하세요):
{"regions":[["A","A","B"],["C","B","B"],["C","C","B"]]}"""


class ClipboardError(RuntimeError):
    """운영체제 클립보드에 접근할 수 없을 때 발생한다."""


def _ensure_clipboard() -> None:
    if not pygame.display.get_init() or pygame.display.get_surface() is None:
        raise ClipboardError("화면이 준비되지 않아 클립보드를 사용할 수 없습니다.")


def copy_text(text: str) -> None:
    """pygame-ce 텍스트 클립보드 API로 Unicode 문자열 하나를 복사한다."""

    if not isinstance(text, str):
        raise TypeError("클립보드에 복사할 값은 문자열이어야 합니다.")
    _ensure_clipboard()
    try:
        pygame.scrap.put_text(text)
    except pygame.error as error:
        raise ClipboardError("클립보드에 텍스트를 복사할 수 없습니다.") from error


def paste_text() -> str:
    """클립보드에서 Unicode JSON 문서 하나를 읽는다."""

    _ensure_clipboard()
    try:
        text = pygame.scrap.get_text()
    except pygame.error as error:
        raise ClipboardError("클립보드에서 텍스트를 읽을 수 없습니다.") from error
    if not text:
        raise ClipboardError("클립보드에 붙여넣을 텍스트가 없습니다.")
    return text.removeprefix("\ufeff")

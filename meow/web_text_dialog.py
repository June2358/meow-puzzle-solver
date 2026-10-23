"""Application-specific browser dialog labels and instructions."""

from puzzle_common.web_text_dialog import WebTextDialog


def open_json_dialog() -> WebTextDialog:
    """Open an editable textarea for user-driven JSON paste."""

    return WebTextDialog(
        title="JSON 입력",
        description="복사한 N×N 영역 JSON을 아래 칸에 붙여넣고 불러오기를 누르세요.",
        text="",
        editable=True,
    )


def open_prompt_dialog(text: str) -> WebTextDialog:
    """Show selectable read-only prompt text without Clipboard API access."""

    return WebTextDialog(
        title="이미지 전사 프롬프트",
        description="아래 텍스트를 선택한 뒤 브라우저의 시스템 복사를 사용하세요.",
        text=text,
        editable=False,
    )

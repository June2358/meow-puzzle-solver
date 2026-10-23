import pygame
import pytest

from puzzle_common import clipboard


@pytest.fixture
def display():
    pygame.display.init()
    pygame.display.set_mode((32, 32))
    yield
    pygame.display.quit()


@pytest.mark.parametrize("operation", ("copy_text", "paste_text"))
def test_clipboard_requires_a_display(operation: str) -> None:
    pygame.display.quit()
    args = ("text",) if operation == "copy_text" else ()

    with pytest.raises(clipboard.ClipboardError, match="화면이 준비되지 않아"):
        getattr(clipboard, operation)(*args)


def test_clipboard_rejects_non_string_copy() -> None:
    with pytest.raises(TypeError, match="문자열"):
        clipboard.copy_text(123)


def test_clipboard_preserves_unicode_and_removes_only_the_leading_bom(
    display, monkeypatch: pytest.MonkeyPatch
) -> None:
    copied: list[str] = []
    text = '한글 <>&\n{"regions": [["A"]]}\ufeff'
    monkeypatch.setattr(pygame.scrap, "put_text", copied.append)
    monkeypatch.setattr(pygame.scrap, "get_text", lambda: "\ufeff" + text)

    clipboard.copy_text(text)

    assert copied == [text]
    assert clipboard.paste_text() == text


@pytest.mark.parametrize("operation", ("copy_text", "paste_text"))
def test_clipboard_preserves_the_cause_of_native_errors(
    display, monkeypatch: pytest.MonkeyPatch, operation: str
) -> None:
    def fail(*args):
        raise pygame.error("SDL clipboard failed")

    native_operation = "put_text" if operation == "copy_text" else "get_text"
    monkeypatch.setattr(pygame.scrap, native_operation, fail)
    args = ("text",) if operation == "copy_text" else ()

    with pytest.raises(clipboard.ClipboardError) as error:
        getattr(clipboard, operation)(*args)

    assert isinstance(error.value.__cause__, pygame.error)


def test_clipboard_rejects_empty_paste(
    display, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(pygame.scrap, "get_text", lambda: "")

    with pytest.raises(clipboard.ClipboardError, match="붙여넣을 텍스트가 없습니다"):
        clipboard.paste_text()

import json
from html import unescape
from types import SimpleNamespace

import pygame
import pytest

import puzzle_common.input_dialog as common_input
import puzzle_common.web_text_dialog as web_text_dialog
from meow.input_dialog import MeowInputDialog
from sudoku.input_dialog import SudokuInputDialog


class FakeElement:
    def __init__(self, document: "FakeDocument", tag_name: str) -> None:
        self.document = document
        self.tagName = tag_name.upper()
        self.id = ""
        self.children: list[FakeElement] = []
        self.parent: FakeElement | None = None
        self.dataset = SimpleNamespace(action="")
        self.style = SimpleNamespace(cssText="")
        self.attributes: dict[str, str] = {}
        self.textContent = ""
        self._innerHTML = ""
        self.value = ""
        self.hidden = False
        self.removed = False
        self.focus_calls = 0
        self.select_calls = 0

    @property
    def innerHTML(self) -> str:
        return self._innerHTML

    @innerHTML.setter
    def innerHTML(self, value: str) -> None:
        self._innerHTML = value
        self.textContent = unescape(value)
        if self.tagName == "TEXTAREA":
            self.value = self.textContent

    def appendChild(self, child: "FakeElement") -> None:
        child.parent = self
        self.children.append(child)

    def setAttribute(self, name: str, value: str) -> None:
        self.attributes[name] = value

    def remove(self) -> None:
        if self.parent is not None:
            self.parent.children.remove(self)
            self.parent = None
        self.removed = True

    def focus(self) -> None:
        self.focus_calls += 1
        self.document.activeElement = self

    def select(self) -> None:
        self.select_calls += 1

    def descendants(self):  # noqa: ANN201
        yield self
        for child in self.children:
            yield from child.descendants()


class FakeDocument:
    def __init__(self) -> None:
        self.body = FakeElement(self, "body")
        self.activeElement: FakeElement | None = None
        self.canvas = FakeElement(self, "canvas")
        self.body.appendChild(self.canvas)

    def createElement(self, tag_name: str) -> FakeElement:
        return FakeElement(self, tag_name)

    def getElementById(self, element_id: str) -> FakeElement | None:
        return next(
            (node for node in self.body.descendants() if node.id == element_id),
            None,
        )

    def querySelector(self, selector: str) -> FakeElement | None:
        if selector == "canvas":
            return self.canvas
        return None


@pytest.fixture
def document(monkeypatch: pytest.MonkeyPatch) -> FakeDocument:
    fake = FakeDocument()
    monkeypatch.setattr(web_text_dialog, "_browser_document", lambda: fake)
    return fake


@pytest.fixture(
    params=[
        (
            MeowInputDialog,
            {"regions": [["A", "A", "B"], ["C", "B", "B"], ["C", "C", "B"]]},
            "복사한 N×N 영역 JSON을 아래 칸에 붙여넣고 불러오기를 누르세요.",
        ),
        (
            SudokuInputDialog,
            [[0] * 9 for _ in range(9)],
            "복사한 9×9 JSON을 아래 칸에 붙여넣고 불러오기를 누르세요.",
        ),
    ],
    ids=["meow", "sudoku"],
)
def editor_case(request):
    return request.param


@pytest.fixture
def input_screen(document, monkeypatch, editor_case):
    pygame.init()
    monkeypatch.setattr(common_input, "is_web_runtime", lambda: True)
    screen = editor_case[0]()
    yield screen
    screen._close_web_text_dialog()
    pygame.quit()


def _find_by_text(document: FakeDocument, text: str) -> FakeElement | None:
    return next(
        (node for node in document.body.descendants() if node.textContent == text),
        None,
    )


def test_json_dialog_returns_exact_pretty_json_and_stays_open_for_validation(
    document: FakeDocument,
    input_screen,
    editor_case,
) -> None:
    input_screen._handle_json_action()
    dialog = input_screen._web_text_dialog
    assert dialog is not None
    overlay = document.getElementById(web_text_dialog._OVERLAY_ID)
    textarea = document.getElementById(web_text_dialog._TEXTAREA_ID)
    error = document.getElementById(web_text_dialog._ERROR_ID)
    load_button = _find_by_text(document, "불러오기")
    pretty_json = json.dumps(editor_case[1], indent=2)

    assert overlay is not None
    assert textarea is not None
    assert error is not None
    assert load_button is not None
    assert (
        _find_by_text(
            document,
            editor_case[2],
        )
        is not None
    )
    assert textarea.focus_calls == 1
    assert "font:16px" in textarea.style.cssText
    assert "safe-area-inset" in overlay.style.cssText
    assert "min-height:48px" in load_button.style.cssText

    textarea.value = pretty_json
    overlay.dataset.action = "submit"

    result = dialog.poll()

    assert result == web_text_dialog.WebTextDialogResult(
        submitted=True,
        text=pretty_json,
    )
    assert dialog.poll() is None
    assert not overlay.removed

    dialog.show_error("JSON 형식 오류")

    assert textarea.value == pretty_json
    assert textarea.focus_calls == 2
    assert error.textContent == "JSON 형식 오류"
    assert error.hidden is False

    dialog.close()

    assert overlay.removed
    assert document.canvas.focus_calls == 1


def test_prompt_dialog_is_read_only_selected_and_cancel_removes_it(
    document: FakeDocument,
    input_screen,
) -> None:
    prompt = '영역/스도쿠 전사 <>&\n한글과 따옴표 "그대로" Return JSON only.'
    input_screen.prompt = prompt
    input_screen._handle_prompt_action()
    dialog = input_screen._web_text_dialog
    assert dialog is not None
    overlay = document.getElementById(web_text_dialog._OVERLAY_ID)
    textarea = document.getElementById(web_text_dialog._TEXTAREA_ID)

    assert overlay is not None
    assert textarea is not None
    assert textarea.value == prompt
    assert textarea.innerHTML.isascii()
    assert unescape(textarea.innerHTML) == prompt
    assert "readonly" in textarea.attributes
    assert textarea.focus_calls == 1
    assert textarea.select_calls == 1
    assert _find_by_text(document, "불러오기") is None
    assert _find_by_text(document, "이미지 전사 프롬프트") is not None

    overlay.dataset.action = "cancel"

    assert dialog.poll() == web_text_dialog.WebTextDialogResult(submitted=False)
    assert overlay.removed
    assert document.canvas.focus_calls == 1


def test_web_runtime_detection_is_strictly_emscripten(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_text_dialog.sys, "platform", "win32")
    assert not web_text_dialog.is_web_runtime()

    monkeypatch.setattr(web_text_dialog.sys, "platform", "emscripten")
    assert web_text_dialog.is_web_runtime()


def test_dom_ui_text_is_ascii_only_and_html_safe(document: FakeDocument) -> None:
    dialog = web_text_dialog.WebTextDialog(
        title="한글 제목 <>&",
        description="설명 <태그> & 안전",
        text="",
        editable=True,
    )
    heading = next(node for node in document.body.descendants() if node.tagName == "H2")
    help_text = next(
        node
        for node in document.body.descendants()
        if node.tagName == "P" and node.id != web_text_dialog._ERROR_ID
    )
    error = document.getElementById(web_text_dialog._ERROR_ID)
    cancel = _find_by_text(document, "취소")

    assert error is not None
    assert cancel is not None
    assert heading.innerHTML.isascii()
    assert help_text.innerHTML.isascii()
    assert cancel.innerHTML.isascii()
    assert heading.textContent == "한글 제목 <>&"
    assert help_text.textContent == "설명 <태그> & 안전"
    assert "&lt;&gt;&amp;" in heading.innerHTML
    assert "<태그>" not in help_text.innerHTML

    dialog.show_error("오류 <script> & 값")

    assert error.innerHTML.isascii()
    assert error.textContent == "오류 <script> & 값"
    assert "<script>" not in error.innerHTML
    assert "&lt;script&gt; &amp;" in error.innerHTML

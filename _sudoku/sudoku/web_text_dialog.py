"""One-shot browser text dialogs backed by real DOM textareas."""

import sys
from contextlib import suppress
from dataclasses import dataclass
from html import escape

_OVERLAY_ID = "sudoku-text-dialog-overlay"
_TEXTAREA_ID = "sudoku-text-dialog-textarea"
_ERROR_ID = "sudoku-text-dialog-error"


class WebTextDialogError(RuntimeError):
    """Raised when the browser DOM bridge cannot operate the text dialog."""


@dataclass(frozen=True)
class WebTextDialogResult:
    """A single acknowledged browser action."""

    submitted: bool
    text: str = ""


def is_web_runtime() -> bool:
    """Return whether the application is running in Pygbag's browser runtime."""

    return sys.platform == "emscripten"


def _browser_document():  # noqa: ANN202
    try:
        import platform

        return platform.document
    except (AttributeError, ImportError) as exc:
        raise WebTextDialogError(
            "브라우저의 텍스트 입력 기능을 사용할 수 없습니다."
        ) from exc


def _ascii_html_text(text: str) -> str:
    """Encode safe visible text as ASCII-only HTML for the Pygbag DOM bridge."""

    escaped = escape(text, quote=False)
    return escaped.encode("ascii", "xmlcharrefreplace").decode("ascii")


def _set_dom_text(element, text: str) -> None:  # noqa: ANN001
    element.innerHTML = _ascii_html_text(text)


class WebTextDialog:
    """Own a temporary DOM overlay and expose its action through polling."""

    def __init__(
        self,
        *,
        title: str,
        description: str,
        text: str,
        editable: bool,
    ) -> None:
        self._document = _browser_document()
        self._overlay = None
        self._textarea = None
        self._error = None
        try:
            self._build(
                title=title,
                description=description,
                text=text,
                editable=editable,
            )
        except Exception as exc:
            self._remove_partial_overlay()
            raise WebTextDialogError(
                "브라우저 텍스트 입력 창을 열 수 없습니다."
            ) from exc

    def _build(
        self,
        *,
        title: str,
        description: str,
        text: str,
        editable: bool,
    ) -> None:
        existing = self._document.getElementById(_OVERLAY_ID)
        if existing is not None:
            existing.remove()

        overlay = self._document.createElement("div")
        self._overlay = overlay
        overlay.id = _OVERLAY_ID
        overlay.dataset.action = ""
        overlay.style.cssText = (
            "position:fixed;inset:0;z-index:10000;background:rgba(15,23,42,.72);"
            "box-sizing:border-box;display:flex;align-items:center;"
            "justify-content:center;overflow:auto;"
            "padding:max(16px,env(safe-area-inset-top)) "
            "max(16px,env(safe-area-inset-right)) "
            "max(16px,env(safe-area-inset-bottom)) "
            "max(16px,env(safe-area-inset-left));"
        )

        card = self._document.createElement("section")
        card.setAttribute("role", "dialog")
        card.setAttribute("aria-modal", "true")
        card.setAttribute("aria-labelledby", "sudoku-text-dialog-title")
        card.style.cssText = (
            "box-sizing:border-box;width:min(640px,100%);max-height:calc(100vh - 32px);"
            "max-height:calc(100dvh - 32px);overflow:auto;background:#fff;"
            "border-radius:14px;padding:clamp(16px,4vw,24px);"
            "box-shadow:0 24px 64px rgba(0,0,0,.35);display:grid;gap:12px;"
        )

        heading = self._document.createElement("h2")
        heading.id = "sudoku-text-dialog-title"
        _set_dom_text(heading, title)
        heading.style.cssText = (
            "margin:0;color:#172554;font:700 22px/1.3 system-ui,sans-serif;"
        )
        card.appendChild(heading)

        help_text = self._document.createElement("p")
        _set_dom_text(help_text, description)
        help_text.style.cssText = (
            "margin:0;color:#475569;font:16px/1.5 system-ui,sans-serif;"
        )
        card.appendChild(help_text)

        textarea = self._document.createElement("textarea")
        self._textarea = textarea
        textarea.id = _TEXTAREA_ID
        textarea.rows = 12
        textarea.value = text
        textarea.autocapitalize = "off"
        textarea.autocomplete = "off"
        textarea.spellcheck = False
        textarea.setAttribute("aria-labelledby", "sudoku-text-dialog-title")
        textarea.style.cssText = (
            "box-sizing:border-box;width:100%;min-height:min(46vh,360px);"
            "max-height:55vh;border:1px solid #94a3b8;border-radius:9px;"
            "padding:12px;color:#0f172a;background:#fff;resize:vertical;"
            "font:16px/1.45 ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;"
            "overscroll-behavior:contain;"
        )
        if not editable:
            textarea.setAttribute("readonly", "")
        card.appendChild(textarea)

        error = self._document.createElement("p")
        self._error = error
        error.id = _ERROR_ID
        _set_dom_text(error, "")
        error.hidden = True
        error.setAttribute("role", "alert")
        error.style.cssText = (
            "margin:0;color:#b91c1c;font:600 15px/1.45 system-ui,sans-serif;"
        )
        card.appendChild(error)

        controls = self._document.createElement("div")
        controls.style.cssText = (
            "display:flex;flex-wrap:wrap;justify-content:flex-end;gap:8px;"
        )
        cancel = self._button("닫기" if not editable else "취소", "cancel")
        controls.appendChild(cancel)
        if editable:
            controls.appendChild(self._button("불러오기", "submit", primary=True))
        card.appendChild(controls)

        overlay.appendChild(card)
        self._document.body.appendChild(overlay)
        textarea.focus()
        if not editable:
            textarea.select()

    def _button(self, label: str, action: str, *, primary: bool = False):  # noqa: ANN202
        button = self._document.createElement("button")
        button.type = "button"
        _set_dom_text(button, label)
        background = "#1e3a8a" if primary else "#f8fafc"
        color = "#fff" if primary else "#172554"
        button.style.cssText = (
            "box-sizing:border-box;flex:1 1 120px;min-width:112px;min-height:48px;"
            f"border:1px solid #94a3b8;border-radius:9px;background:{background};"
            f"color:{color};font:600 16px system-ui,sans-serif;touch-action:manipulation;"
        )
        button.setAttribute(
            "onclick",
            f"document.getElementById('{_OVERLAY_ID}').dataset.action='{action}'",
        )
        return button

    def poll(self) -> WebTextDialogResult | None:
        """Return one submit/cancel action without closing a submitted dialog."""

        overlay = self._overlay
        textarea = self._textarea
        if overlay is None or textarea is None:
            return None
        try:
            action = str(overlay.dataset.action)
            if not action:
                return None
            overlay.dataset.action = ""
            if action == "submit":
                return WebTextDialogResult(submitted=True, text=str(textarea.value))
            if action == "cancel":
                self.close()
                return WebTextDialogResult(submitted=False)
        except WebTextDialogError:
            raise
        except Exception as exc:
            raise WebTextDialogError(
                "브라우저 텍스트 입력 결과를 확인할 수 없습니다."
            ) from exc
        raise WebTextDialogError("브라우저 텍스트 입력 동작을 확인할 수 없습니다.")

    def show_error(self, message: str) -> None:
        """Keep the original text visible and show a validation error in the modal."""

        if self._error is None or self._textarea is None:
            raise WebTextDialogError("브라우저 입력 오류를 표시할 수 없습니다.")
        try:
            _set_dom_text(self._error, message)
            self._error.hidden = False
            self._textarea.focus()
        except Exception as exc:
            raise WebTextDialogError(
                "브라우저 입력 오류를 표시할 수 없습니다."
            ) from exc

    def close(self) -> None:
        """Remove the overlay and return focus to the pygame canvas when possible."""

        overlay = self._overlay
        if overlay is None:
            return
        try:
            overlay.remove()
        except Exception as exc:
            raise WebTextDialogError(
                "브라우저 텍스트 입력 창을 닫을 수 없습니다."
            ) from exc
        finally:
            self._overlay = None
            self._textarea = None
            self._error = None
            self._focus_canvas()

    def _focus_canvas(self) -> None:
        try:
            canvas = self._document.querySelector("canvas")
            if canvas is not None:
                canvas.focus()
        except Exception:
            # Focus restoration is a convenience after the overlay is already gone.
            pass

    def _remove_partial_overlay(self) -> None:
        overlay = self._overlay
        self._overlay = None
        self._textarea = None
        self._error = None
        if overlay is None:
            return
        with suppress(Exception):
            overlay.remove()


def open_json_dialog() -> WebTextDialog:
    """Open an editable textarea for user-driven JSON paste."""

    return WebTextDialog(
        title="JSON 입력",
        description="복사한 9×9 JSON을 아래 칸에 붙여넣고 불러오기를 누르세요.",
        text="",
        editable=True,
    )


def open_prompt_dialog(text: str) -> WebTextDialog:
    """Show selectable read-only prompt text without Clipboard API access."""

    return WebTextDialog(
        title="OCR 프롬프트",
        description="아래 텍스트를 선택한 뒤 브라우저의 시스템 복사를 사용하세요.",
        text=text,
        editable=False,
    )

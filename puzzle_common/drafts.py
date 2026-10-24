"""Keep each browser tab's puzzle drafts across reloads."""

import json
from collections.abc import Iterable
from contextlib import suppress

from .puzzle import PuzzleDefinition
from .runtime import browser_window
from .view import Grid
from .web_text_dialog import is_web_runtime

_KEY_PREFIX = "puzzle-solvers.draft."


def save_draft(definition: PuzzleDefinition, grid: Grid) -> None:
    if not is_web_runtime():
        return
    # Browser privacy settings or quotas must not prevent editing.
    with suppress(Exception):
        browser_window().sessionStorage.setItem(
            _KEY_PREFIX + definition.key, json.dumps(grid, ensure_ascii=False)
        )


def load_drafts(definitions: Iterable[PuzzleDefinition]) -> dict[str, Grid]:
    restored = {}
    if is_web_runtime():
        for definition in definitions:
            try:
                text = browser_window().sessionStorage.getItem(
                    _KEY_PREFIX + definition.key
                )
                if text:
                    restored[definition.key] = definition.normalize(
                        json.loads(str(text))
                    )
            except Exception:
                continue
    return restored

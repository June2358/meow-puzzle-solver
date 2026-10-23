import asyncio
from types import SimpleNamespace

import pygame
import pytest

from puzzle_common.presentation import Outcome, PlaybackData


def screen(value):
    async def run():
        return value

    return SimpleNamespace(run=run)


@pytest.fixture
def lifecycle(monkeypatch):
    calls = []
    monkeypatch.setattr(pygame, "init", lambda: calls.append("init"))
    monkeypatch.setattr(pygame, "quit", lambda: calls.append("quit"))
    monkeypatch.setattr(pygame.key, "stop_text_input", lambda: None)
    return calls


@pytest.mark.parametrize("outcome", (Outcome.UNIQUE, Outcome.MULTIPLE))
def test_shared_flow_reopens_editor_with_the_returned_draft(lifecycle, outcome):
    from puzzle_common.app import run_app

    puzzle, draft, edited = object(), object(), object()
    result = PlaybackData(outcome, (object(),))
    inputs = iter((puzzle, None))
    edits = []

    def editor(previous, error):
        edits.append((previous, error))
        return screen(next(inputs))

    def solver(received):
        assert received is puzzle
        return result

    def player(received, solved):
        assert (received, solved) == (puzzle, result)
        return screen(edited)

    asyncio.run(run_app(editor, solver, player, lambda _: draft))

    assert edits == [(None, None), (edited, None)]
    assert lifecycle == ["init", "quit"]


def test_shared_flow_keeps_draft_and_error_when_result_cannot_be_shown(lifecycle):
    from puzzle_common.app import run_app

    puzzle, draft = object(), object()
    result = PlaybackData(Outcome.UNSOLVABLE, (object(),))
    inputs = iter((puzzle, None))
    edits = []

    def editor(previous, error):
        edits.append((previous, error))
        return screen(next(inputs))

    def forbidden_player(*args):
        pytest.fail("Invalid results must return to the editor")

    asyncio.run(
        run_app(
            editor,
            lambda _: result,
            forbidden_player,
            lambda _: draft,
        )
    )

    assert edits == [
        (None, None),
        (draft, "현재 입력으로 가능한 해가 없습니다. 원본 문제와 입력을 확인하세요."),
    ]
    assert lifecycle == ["init", "quit"]


def test_shared_flow_quits_if_editor_construction_raises(lifecycle):
    from puzzle_common.app import run_app

    def failing_editor(*args):
        raise RuntimeError("editor failed")

    with pytest.raises(RuntimeError, match="editor failed"):
        asyncio.run(run_app(failing_editor, lambda _: None, screen, lambda _: None))

    assert lifecycle == ["init", "quit"]

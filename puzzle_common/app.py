"""One editor/solver/playback lifecycle for every puzzle application."""

from collections.abc import Callable
from typing import Protocol

import pygame

from .presentation import Outcome, PlaybackData

UNSOLVABLE_MESSAGE = (
    "현재 입력으로 가능한 해가 없습니다. 원본 문제와 입력을 확인하세요."
)


class Screen[T](Protocol):
    async def run(self) -> T | None: ...


async def run_app[Puzzle, Draft, Frame](
    create_editor: Callable[[Draft | None, str | None], Screen[Puzzle]],
    solve: Callable[[Puzzle], PlaybackData[Frame]],
    create_player: Callable[[Puzzle, PlaybackData[Frame]], Screen[Draft]],
    get_draft: Callable[[Puzzle], Draft],
) -> None:
    pygame.init()
    draft: Draft | None = None
    error: str | None = None
    try:
        pygame.key.stop_text_input()
        while True:
            puzzle = await create_editor(draft, error).run()
            if puzzle is None:
                return
            draft = get_draft(puzzle)
            result = solve(puzzle)
            error = UNSOLVABLE_MESSAGE if result.outcome is Outcome.UNSOLVABLE else None
            if error is not None:
                continue
            draft = await create_player(puzzle, result).run()
            if draft is None:
                return
    finally:
        pygame.quit()

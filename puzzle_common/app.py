"""One editor/solver/playback lifecycle for every puzzle application."""

from collections.abc import Callable
from typing import Protocol

import pygame


class Screen[T](Protocol):
    async def run(self) -> T | None: ...


async def run_app[Puzzle, Draft, Result](
    create_editor: Callable[[Draft | None, str | None], Screen[Puzzle]],
    solve: Callable[[Puzzle], Result],
    create_player: Callable[[Puzzle, Result], Screen[Draft]],
    get_draft: Callable[[Puzzle], Draft],
    get_error: Callable[[Result], str | None] | None = None,
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
            error = get_error(result) if get_error is not None else None
            if error is not None:
                continue
            draft = await create_player(puzzle, result).run()
            if draft is None:
                return
    finally:
        pygame.quit()

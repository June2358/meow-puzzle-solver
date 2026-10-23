"""One editor/solver/playback lifecycle for every puzzle application."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

import pygame

from .engine import Outcome, SolveResult

UNSOLVABLE_MESSAGE = (
    "현재 입력으로 가능한 해가 없습니다. 원본 문제와 입력을 확인하세요."
)


class Screen[T](Protocol):
    async def run(self) -> T | None: ...


@dataclass(frozen=True, slots=True)
class PuzzlePlugin[Puzzle, Draft, Result: SolveResult]:
    """Register a puzzle's screens, solver and draft using one app contract."""

    create_editor: Callable[[Draft | None, str | None], Screen[Puzzle]]
    solve: Callable[[Puzzle], Result]
    create_player: Callable[[Puzzle, Result], Screen[Draft]]
    get_draft: Callable[[Puzzle], Draft]


async def run_app[Puzzle, Draft, Result: SolveResult](
    plugin: PuzzlePlugin[Puzzle, Draft, Result],
) -> None:
    pygame.init()
    draft: Draft | None = None
    error: str | None = None
    try:
        pygame.key.stop_text_input()
        while True:
            puzzle = await plugin.create_editor(draft, error).run()
            if puzzle is None:
                return
            draft = plugin.get_draft(puzzle)
            result = plugin.solve(puzzle)
            error = UNSOLVABLE_MESSAGE if result.outcome is Outcome.UNSOLVABLE else None
            if error is not None:
                continue
            draft = await plugin.create_player(puzzle, result).run()
            if draft is None:
                return
    finally:
        pygame.quit()

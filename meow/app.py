"""MEOW Queens 퍼즐의 입력과 풀이를 연결하는 pygame 앱 흐름."""

import pygame

from .input_dialog import MeowInputDialog
from .model import RegionGrid
from .solver import solve
from .visualizer import MeowVisualizer


async def main() -> None:
    """화면을 닫을 때까지 입력·풀이·시각화 흐름을 반복한다."""

    pygame.init()
    pygame.key.stop_text_input()
    draft: RegionGrid | None = None

    try:
        while True:
            dialog = MeowInputDialog(initial_grid=draft)
            puzzle = await dialog.run()
            if puzzle is None:
                return

            draft = puzzle.region_grid
            result = solve(puzzle)

            visualizer = MeowVisualizer(puzzle, result)
            draft_for_editing = await visualizer.run()
            if draft_for_editing is None:
                return
            draft = draft_for_editing
    finally:
        pygame.quit()

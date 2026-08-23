"""Top-level pygame flow for editing, solving, and replaying MEOW puzzles."""

import pygame

from .input_dialog import MeowInputDialog
from .model import RegionGrid
from .solver import solve
from .visualizer import MeowVisualizer


async def main() -> None:
    """Run one input/solve/visualize loop until either screen closes."""

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

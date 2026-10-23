"""Top-level pygame flow for editing, validating, solving, and replaying."""

from puzzle_common.app import run_app

from .input_dialog import SudokuInputDialog
from .presentation import to_playback
from .solver import SudokuSolver
from .visualizer import SudokuVisualizer


async def main() -> None:
    """Run the application until the user closes either screen."""

    await run_app(
        lambda draft, error: SudokuInputDialog(
            initial_board=draft, initial_error=error
        ),
        lambda puzzle: to_playback(SudokuSolver(puzzle).solve()),
        SudokuVisualizer,
        lambda puzzle: puzzle.grid,
    )

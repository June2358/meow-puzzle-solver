"""Top-level pygame flow for editing and solving MEOW Queens puzzles."""

from puzzle_common.app import run_app

from .input_dialog import MeowInputDialog
from .presentation import to_playback
from .solver import solve
from .visualizer import MeowVisualizer


async def main() -> None:
    """Run one input/solve/visualize loop until either screen closes."""

    await run_app(
        lambda draft, error: MeowInputDialog(initial_grid=draft, initial_error=error),
        lambda puzzle: to_playback(solve(puzzle)),
        MeowVisualizer,
        lambda puzzle: puzzle.region_grid,
    )

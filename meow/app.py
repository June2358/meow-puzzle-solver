"""Top-level pygame flow for editing and solving MEOW Queens puzzles."""

from puzzle_common.app import PuzzlePlugin

from .input_dialog import MeowInputDialog
from .solver import solve
from .visualizer import MeowVisualizer

PLUGIN = PuzzlePlugin(
    create_editor=MeowInputDialog,
    solve=solve,
    create_player=MeowVisualizer,
    get_draft=lambda puzzle: puzzle.region_grid,
)

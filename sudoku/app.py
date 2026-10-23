"""Top-level pygame flow for editing, validating, solving, and replaying."""

from puzzle_common.app import PuzzlePlugin

from .input_dialog import SudokuInputDialog
from .presentation import to_playback
from .solver import SudokuSolver
from .visualizer import SudokuVisualizer

PLUGIN = PuzzlePlugin(
    create_editor=SudokuInputDialog,
    solve=lambda puzzle: to_playback(SudokuSolver(puzzle).solve()),
    create_player=SudokuVisualizer,
    get_draft=lambda puzzle: puzzle.grid,
)

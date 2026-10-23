"""Top-level pygame flow for editing, validating, solving, and replaying."""

from puzzle_common.app import PuzzlePlugin

from .input_dialog import SudokuInputDialog
from .solver import SudokuSolver
from .visualizer import SudokuVisualizer

PLUGIN = PuzzlePlugin(
    create_editor=SudokuInputDialog,
    solve=lambda puzzle: SudokuSolver(puzzle).solve(),
    create_player=SudokuVisualizer,
    get_draft=lambda puzzle: puzzle.grid,
)

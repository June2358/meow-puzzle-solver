"""Top-level pygame flow for editing, validating, solving, and replaying."""

from puzzle_common.app import run_app

from .input_dialog import SudokuInputDialog
from .solve_types import SolveStatus
from .solver import SudokuSolver
from .visualizer import SudokuVisualizer

_UNSOLVABLE_MESSAGE = (
    "현재 단서로 가능한 해가 없습니다. 빨간 중복 외의 OCR 오인식도 확인하세요."
)


async def main() -> None:
    """Run the application until the user closes either screen."""

    await run_app(
        lambda draft, error: SudokuInputDialog(
            initial_board=draft, initial_error=error
        ),
        lambda puzzle: SudokuSolver(puzzle).solve(),
        SudokuVisualizer,
        lambda puzzle: puzzle.grid,
        lambda result: (
            _UNSOLVABLE_MESSAGE if result.status is SolveStatus.UNSOLVABLE else None
        ),
    )

"""입력·검증·풀이·재생을 연결하는 pygame 앱 흐름."""

import pygame

from .board import Grid
from .input_dialog import SudokuInputDialog
from .solve_types import SolveStatus
from .solver import SudokuSolver
from .visualizer import SudokuVisualizer

_UNSOLVABLE_MESSAGE = (
    "현재 단서로 가능한 해가 없습니다. 빨간 중복 외의 OCR 오인식도 확인하세요."
)


async def main() -> None:
    """사용자가 화면을 닫을 때까지 앱을 실행한다."""

    pygame.init()
    pygame.key.stop_text_input()
    draft: Grid | None = None
    input_error: str | None = None

    try:
        while True:
            dialog = SudokuInputDialog(
                initial_board=draft,
                initial_error=input_error,
            )
            puzzle = await dialog.run()
            if puzzle is None:
                return

            draft = puzzle.grid
            result = SudokuSolver(puzzle).solve()
            if result.status is SolveStatus.UNSOLVABLE:
                input_error = _UNSOLVABLE_MESSAGE
                continue

            input_error = None
            visualizer = SudokuVisualizer(puzzle, result)
            draft_for_editing = await visualizer.run()
            if draft_for_editing is None:
                return
            draft = draft_for_editing
    finally:
        pygame.quit()

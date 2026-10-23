"""정답 탐색 없이 결정적 추론을 고정점까지 적용하는 솔버."""

from __future__ import annotations

from .model import Puzzle
from .solve_types import LogicResult, LogicStatus, LogicStep
from .state import LogicState
from .techniques import find_next_deduction


class LogicSolver:
    """순수 finder를 하나씩 적용하며 설명 가능한 trace를 만든다."""

    def __init__(self, puzzle: Puzzle) -> None:
        self.puzzle = puzzle

    def solve(self, initial_state: LogicState | None = None) -> LogicResult:
        """논리 기법이 더는 없거나 완성/모순에 이를 때까지 진행한다.

        전달받은 ``initial_state``는 clone해서 사용하므로 호출자의 상태도
        변경하지 않는다.
        """

        if initial_state is None:
            state = LogicState(self.puzzle)
        else:
            if initial_state.puzzle != self.puzzle:
                raise ValueError("initial_state는 같은 퍼즐에 속해야 합니다.")
            state = initial_state.clone()

        initial_snapshot = state.snapshot()
        steps: list[LogicStep] = []

        while True:
            before = state.snapshot()
            message = before.contradiction_message()
            if message is not None:
                status = LogicStatus.CONTRADICTION
                break

            deduction = find_next_deduction(before)
            if deduction is None:
                if before.is_solved():
                    status = LogicStatus.SOLVED_LOGICALLY
                    message = "결정적 추론만으로 해결했습니다."
                else:
                    status = LogicStatus.STALLED
                    message = "현재 구현된 논리 기법으로 더 진행할 수 없습니다."
                break

            changed = False
            for cell in deduction.placements:
                changed = state.place_cat(cell) or changed
            for cell in deduction.exclusions:
                changed = state.exclude(cell) or changed
            if not changed:
                raise RuntimeError("finder가 상태를 바꾸지 않는 추론을 반환했습니다.")

            step = LogicStep(
                number=len(steps) + 1,
                deduction=deduction,
                before=before,
                after=state.snapshot(),
            )
            steps.append(step)

        return LogicResult(
            status=status,
            initial_state=initial_snapshot,
            final_state=before,
            steps=tuple(steps),
            message=message,
        )


def solve_logically(
    puzzle: Puzzle,
    initial_state: LogicState | None = None,
) -> LogicResult:
    """한 번의 논리 풀이를 위한 간단한 공개 진입점."""

    return LogicSolver(puzzle).solve(initial_state)

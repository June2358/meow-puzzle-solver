"""정답 탐색 없이 결정적 추론을 고정점까지 적용하는 솔버."""

from __future__ import annotations

from puzzle_common.engine import Engine, LogicRun

from .engine_adapter import MeowDomain
from .model import Puzzle
from .state import LogicState


class LogicSolver:
    """순수 finder를 하나씩 적용하며 설명 가능한 trace를 만든다."""

    def __init__(self, puzzle: Puzzle) -> None:
        self.puzzle = puzzle

    def solve(self, initial_state: LogicState | None = None) -> LogicRun:
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

        return Engine(MeowDomain()).propagate(state)


def solve_logically(
    puzzle: Puzzle,
    initial_state: LogicState | None = None,
) -> LogicRun:
    """한 번의 논리 풀이를 위한 간단한 공개 진입점."""

    return LogicSolver(puzzle).solve(initial_state)

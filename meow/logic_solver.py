"""정답 탐색 없이 결정적 추론을 고정점까지 적용하는 솔버."""

from __future__ import annotations

from itertools import combinations

from .model import Puzzle
from .solve_types import LogicResult, LogicStatus, LogicStep
from .state import LogicSnapshot, LogicState
from .techniques import find_next_deduction


def _contradiction_message(snapshot: LogicSnapshot) -> str | None:
    """고양이 충돌이나 비어 버린 exact-one 단위를 보고한다."""

    puzzle = snapshot.puzzle
    for first, second in combinations(sorted(snapshot.cats), 2):
        if second in puzzle.conflicts[first]:
            return (
                f"R{first[0] + 1}C{first[1] + 1}과 "
                f"R{second[0] + 1}C{second[1] + 1}의 고양이가 충돌합니다."
            )

    named_groups = (
        ("행", puzzle.rows),
        ("열", puzzle.cols),
        ("영역", puzzle.regions),
    )
    for name, units in named_groups:
        for index, unit in enumerate(units):
            if not snapshot.cats_in(unit) and not snapshot.candidates_for(unit):
                return f"{name} {index + 1}에 가능한 칸이 없습니다."
    return None


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
            contradiction = _contradiction_message(before)
            if contradiction is not None:
                return LogicResult(
                    status=LogicStatus.CONTRADICTION,
                    initial_state=initial_snapshot,
                    final_state=before,
                    steps=tuple(steps),
                    message=contradiction,
                )

            deduction = find_next_deduction(before)
            if deduction is None:
                if before.is_solved():
                    return LogicResult(
                        status=LogicStatus.SOLVED_LOGICALLY,
                        initial_state=initial_snapshot,
                        final_state=before,
                        steps=tuple(steps),
                        message="결정적 추론만으로 해결했습니다.",
                    )
                return LogicResult(
                    status=LogicStatus.STALLED,
                    initial_state=initial_snapshot,
                    final_state=before,
                    steps=tuple(steps),
                    message="현재 구현된 논리 기법으로 더 진행할 수 없습니다.",
                )

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


def solve_logically(
    puzzle: Puzzle,
    initial_state: LogicState | None = None,
) -> LogicResult:
    """한 번의 논리 풀이를 위한 간단한 공개 진입점."""

    return LogicSolver(puzzle).solve(initial_state)

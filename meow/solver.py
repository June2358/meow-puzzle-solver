"""결정적 추론, 한 단계 가정, 분기 탐색을 순서대로 실행하는 풀이 코어.

Exact verifier는 해의 개수만 독립적으로 판정한다. 실제 풀이는 exact가
찾은 좌표를 읽지 않고, 마지막에 해의 존재 여부만 교차 검증한다.
"""

from __future__ import annotations

from itertools import combinations

from puzzle_common.engine import Engine, LogicStatus, Outcome, SolveResult

from .engine_adapter import MeowDomain
from .exact_solver import ExactResult, ExactStatus, Solution, verify_exact
from .model import Puzzle
from .state import LogicState


def _valid_solution(puzzle: Puzzle, solution: Solution) -> bool:
    cells = frozenset(solution)
    if len(solution) != puzzle.size or len(cells) != puzzle.size:
        return False
    if {row for row, _ in cells} != set(range(puzzle.size)):
        return False
    if {column for _, column in cells} != set(range(puzzle.size)):
        return False
    if {puzzle.region_of(cell) for cell in cells} != set(range(puzzle.size)):
        return False
    return all(
        second not in puzzle.conflicts[first]
        for first, second in combinations(cells, 2)
    )


class Solver:
    """해를 분류한 뒤 결정적 추론, 한 단계 가정, 분기 탐색을 실행한다."""

    def __init__(self, puzzle: Puzzle) -> None:
        if not isinstance(puzzle, Puzzle):
            raise TypeError("Solver는 Puzzle을 필요로 합니다.")
        self.puzzle = puzzle

    def solve(self) -> SolveResult:
        """첫 유효 해 또는 해 없음을 반환한다."""

        exact_result = verify_exact(self.puzzle)
        run = Engine(MeowDomain()).solve(LogicState(self.puzzle), solution_limit=1)
        outcome = {
            ExactStatus.UNIQUE: Outcome.UNIQUE,
            ExactStatus.MULTIPLE: Outcome.MULTIPLE,
            ExactStatus.UNSOLVABLE: Outcome.UNSOLVABLE,
        }[exact_result.status]
        result = SolveResult(outcome, run)
        self._check_exact_consistency(result, exact_result)
        return result

    def _check_exact_consistency(
        self, result: SolveResult, exact_result: ExactResult
    ) -> None:
        """풀이가 exact 해 좌표를 읽지 않은 채 해의 존재 여부를 교차 검증한다."""

        exact_has_solution = exact_result.status is not ExactStatus.UNSOLVABLE
        solver_has_solution = result.solution is not None
        if exact_has_solution != solver_has_solution:
            raise RuntimeError("Exact 판정과 솔버의 해 존재 여부가 다릅니다.")
        if result.solution is not None and not _valid_solution(
            self.puzzle,
            tuple(sorted(result.solution.cats)),
        ):
            raise RuntimeError("솔버가 유효하지 않은 해를 반환했습니다.")
        if (
            result.run.initial_logic_result.status is LogicStatus.SOLVED
            and exact_result.status is not ExactStatus.UNIQUE
        ):
            raise RuntimeError(
                "결정적 추론 완성과 exact 유일해 판정이 일치하지 않습니다."
            )


def solve(puzzle: Puzzle) -> SolveResult:
    """퍼즐 하나를 풀고 해의 개수를 검증한다."""

    return Solver(puzzle).solve()

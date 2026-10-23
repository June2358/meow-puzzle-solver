"""결정적 추론, 한 단계 가정, 분기 탐색을 순서대로 실행하는 풀이 코어.

Exact verifier는 해의 개수만 독립적으로 판정한다. 실제 풀이는 exact가
찾은 좌표를 읽지 않고, 마지막에 해의 존재 여부만 교차 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from itertools import combinations

from puzzle_common.engine import Engine

from .engine_adapter import MeowDomain, logic_result_from
from .exact_solver import ExactResult, ExactStatus, Solution, verify_exact
from .model import Cell, Puzzle
from .solve_types import LogicResult, LogicStatus
from .state import LogicSnapshot, LogicState


class SolveOutcome(StrEnum):
    """솔버가 답을 얻은 단계."""

    SOLVED_WITH_LOGIC = "SOLVED_WITH_LOGIC"
    SOLVED_WITH_PROBING = "SOLVED_WITH_PROBING"
    SOLVED_WITH_BACKTRACK_SEARCH = "SOLVED_WITH_BACKTRACK_SEARCH"
    UNSOLVABLE = "UNSOLVABLE"


@dataclass(frozen=True, slots=True)
class ProbeResult:
    """후보 하나를 고양이로 가정하고 결정적 추론만 실행한 결과."""

    assumption: Cell
    logic_result: LogicResult

    @property
    def status(self) -> LogicStatus:
        return self.logic_result.status


@dataclass(frozen=True, slots=True)
class ProbingRound:
    """중첩 없이 새 CAT을 만드는 후보들을 시험한 한 단계 가정 한 번."""

    before: LogicSnapshot
    candidates: tuple[Cell, ...]
    probes: tuple[ProbeResult, ...]
    elimination: LogicResult | None = None

    @property
    def stalled(self) -> bool:
        return (
            self.elimination is None
            and len(self.probes) == len(self.candidates)
            and all(result.status is LogicStatus.STALLED for result in self.probes)
        )


@dataclass(frozen=True, slots=True)
class SolveResult:
    """해 분류, 결정적 추론, 한 단계 가정 결과와 표시할 해."""

    outcome: SolveOutcome
    exact_result: ExactResult
    initial_logic_result: LogicResult
    solution: Solution | None
    probing_rounds: tuple[ProbingRound, ...] = ()
    used_backtrack_search: bool = False


def _solution_from(snapshot: LogicSnapshot) -> Solution:
    if not snapshot.is_solved():
        raise RuntimeError("완성되지 않은 상태를 해로 반환할 수 없습니다.")
    return tuple(sorted(snapshot.cats))


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
        initial_logic = logic_result_from(run.initial_logic_result)
        rounds = tuple(
            ProbingRound(
                before=round_.before,
                candidates=round_.candidates,
                probes=tuple(
                    ProbeResult(probe.assumption, logic_result_from(probe.logic_result))
                    for probe in round_.probes
                ),
                elimination=(
                    logic_result_from(round_.elimination)
                    if round_.elimination is not None
                    else None
                ),
            )
            for round_ in run.probing_rounds
        )
        solution = _solution_from(run.solutions[0]) if run.solutions else None
        used_backtrack_search = run.used_backtrack_search
        if solution is None:
            outcome = SolveOutcome.UNSOLVABLE
        elif initial_logic.status is LogicStatus.SOLVED_LOGICALLY:
            outcome = SolveOutcome.SOLVED_WITH_LOGIC
        elif used_backtrack_search:
            outcome = SolveOutcome.SOLVED_WITH_BACKTRACK_SEARCH
        else:
            outcome = SolveOutcome.SOLVED_WITH_PROBING

        result = SolveResult(
            outcome=outcome,
            exact_result=exact_result,
            initial_logic_result=initial_logic,
            solution=solution,
            probing_rounds=rounds,
            used_backtrack_search=used_backtrack_search,
        )
        self._check_exact_consistency(result)
        return result

    def _check_exact_consistency(self, result: SolveResult) -> None:
        """풀이가 exact 해 좌표를 읽지 않은 채 해의 존재 여부를 교차 검증한다."""

        exact_has_solution = result.exact_result.status is not ExactStatus.UNSOLVABLE
        solver_has_solution = result.solution is not None
        if exact_has_solution != solver_has_solution:
            raise RuntimeError("Exact 판정과 솔버의 해 존재 여부가 다릅니다.")
        if result.solution is not None and not _valid_solution(
            self.puzzle,
            result.solution,
        ):
            raise RuntimeError("솔버가 유효하지 않은 해를 반환했습니다.")
        if (
            result.outcome is SolveOutcome.SOLVED_WITH_LOGIC
            and result.exact_result.status is not ExactStatus.UNIQUE
        ):
            raise RuntimeError(
                "결정적 추론 완성과 exact 유일해 판정이 일치하지 않습니다."
            )


def solve(puzzle: Puzzle) -> SolveResult:
    """퍼즐 하나를 풀고 해의 개수를 검증한다."""

    return Solver(puzzle).solve()

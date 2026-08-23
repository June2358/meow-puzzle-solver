"""기본 로직, 귀류법, 백트래킹을 순서대로 실행하는 풀이 코어.

Exact verifier는 해의 개수만 독립적으로 판정한다. 실제 풀이는 exact가
찾은 좌표를 읽지 않고, 마지막에 해의 존재 여부만 교차 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from itertools import combinations
from typing import Final

from .exact_solver import ExactResult, ExactStatus, Solution, verify_exact
from .logic_solver import solve_logically
from .model import Cell, Puzzle, Unit
from .solve_types import (
    Deduction,
    LogicResult,
    LogicStatus,
    LogicStep,
    Technique,
    UnitKind,
    UnitRef,
)
from .state import LogicSnapshot, LogicState


class SolveOutcome(StrEnum):
    """솔버가 답을 얻은 단계."""

    SOLVED_WITH_LOGIC = "SOLVED_WITH_LOGIC"
    SOLVED_WITH_REFUTATION = "SOLVED_WITH_REFUTATION"
    SOLVED_WITH_BACKTRACKING = "SOLVED_WITH_BACKTRACKING"
    UNSOLVABLE = "UNSOLVABLE"


@dataclass(frozen=True, slots=True)
class AssumptionResult:
    """후보 하나를 가정하고 기본 로직만 실행한 결과."""

    assumption: Cell
    logic_result: LogicResult

    @property
    def status(self) -> LogicStatus:
        return self.logic_result.status


@dataclass(frozen=True, slots=True)
class RefutationRound:
    """중첩 없이 한 단위의 후보를 시험한 귀류법 한 번."""

    before: LogicSnapshot
    selected_unit: UnitRef
    candidates: tuple[Cell, ...]
    assumptions: tuple[AssumptionResult, ...]
    elimination: LogicResult | None = None

    @property
    def stalled(self) -> bool:
        return (
            self.elimination is None
            and len(self.assumptions) == len(self.candidates)
            and all(result.status is LogicStatus.STALLED for result in self.assumptions)
        )


@dataclass(frozen=True, slots=True)
class SolveResult:
    """해 분류, 기본 로직, 귀류법 결과와 표시할 해."""

    outcome: SolveOutcome
    exact_result: ExactResult
    initial_logic_result: LogicResult
    solution: Solution | None
    refutation_rounds: tuple[RefutationRound, ...] = ()
    used_backtracking: bool = False


_UNIT_KIND_ORDER: Final[tuple[UnitKind, ...]] = (
    UnitKind.ROW,
    UnitKind.COLUMN,
    UnitKind.REGION,
)


def _units(puzzle: Puzzle, kind: UnitKind) -> tuple[Unit, ...]:
    if kind is UnitKind.ROW:
        return puzzle.rows
    if kind is UnitKind.COLUMN:
        return puzzle.cols
    return puzzle.regions


def _cell_name(cell: Cell) -> str:
    return f"R{cell[0] + 1}C{cell[1] + 1}"


def _solution_from(snapshot: LogicSnapshot) -> Solution:
    if not snapshot.is_solved():
        raise RuntimeError("완성되지 않은 상태를 해로 반환할 수 없습니다.")
    return tuple(sorted(snapshot.cats))


def _select_mrv_unit(snapshot: LogicSnapshot) -> tuple[UnitRef, tuple[Cell, ...]]:
    """행·열·영역 전체에서 후보가 가장 적은 미완성 단위를 고른다."""

    choices: list[tuple[int, int, int, UnitRef, tuple[Cell, ...]]] = []
    for kind_order, kind in enumerate(_UNIT_KIND_ORDER):
        for index, unit in enumerate(_units(snapshot.puzzle, kind)):
            if snapshot.cats_in(unit):
                continue
            candidates = tuple(sorted(snapshot.candidates_for(unit)))
            choices.append(
                (len(candidates), kind_order, index, UnitRef(kind, index), candidates)
            )

    if not choices:
        raise RuntimeError("미완성 상태에 MRV로 선택할 단위가 없습니다.")

    _, _, _, ref, candidates = min(choices, key=lambda choice: choice[:3])
    if not candidates:
        raise RuntimeError("모순 상태가 기본 로직을 통과했습니다.")
    return ref, candidates


def _renumber_steps(
    steps: tuple[LogicStep, ...],
    start: int,
) -> tuple[LogicStep, ...]:
    return tuple(
        replace(step, number=start + offset) for offset, step in enumerate(steps)
    )


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
    """해를 분류한 뒤 기본 로직, 귀류법, 백트래킹을 실행한다."""

    def __init__(self, puzzle: Puzzle) -> None:
        if not isinstance(puzzle, Puzzle):
            raise TypeError("Solver는 Puzzle을 필요로 합니다.")
        self.puzzle = puzzle

    def solve(self) -> SolveResult:
        """첫 유효 해 또는 해 없음을 반환한다."""

        exact_result = verify_exact(self.puzzle)
        initial_logic = solve_logically(self.puzzle)

        if initial_logic.status is LogicStatus.SOLVED_LOGICALLY:
            result = SolveResult(
                outcome=SolveOutcome.SOLVED_WITH_LOGIC,
                exact_result=exact_result,
                initial_logic_result=initial_logic,
                solution=_solution_from(initial_logic.final_state),
            )
        elif initial_logic.status is LogicStatus.CONTRADICTION:
            result = SolveResult(
                outcome=SolveOutcome.UNSOLVABLE,
                exact_result=exact_result,
                initial_logic_result=initial_logic,
                solution=None,
            )
        else:
            rounds, solution, used_backtracking = self._solve_by_refutation(
                initial_logic.final_state
            )
            result = SolveResult(
                outcome=(
                    SolveOutcome.UNSOLVABLE
                    if solution is None
                    else (
                        SolveOutcome.SOLVED_WITH_BACKTRACKING
                        if used_backtracking
                        else SolveOutcome.SOLVED_WITH_REFUTATION
                    )
                ),
                exact_result=exact_result,
                initial_logic_result=initial_logic,
                solution=solution,
                refutation_rounds=rounds,
                used_backtracking=used_backtracking,
            )

        self._check_exact_consistency(result)
        return result

    def _assume_and_propagate(
        self,
        snapshot: LogicSnapshot,
        candidate: Cell,
    ) -> AssumptionResult:
        """후보 하나를 가정하고 기본 로직만 고정점까지 실행한다."""

        assumed = LogicState.from_snapshot(snapshot)
        assumed.place_cat(candidate)
        # 이 함수는 solve_logically()만 호출하므로 가정 안에서
        # 다시 귀류법이나 백트래킹으로 들어갈 수 없다.
        logic_result = solve_logically(self.puzzle, assumed)
        return AssumptionResult(
            assumption=candidate,
            logic_result=logic_result,
        )

    def _apply_contradiction(
        self,
        snapshot: LogicSnapshot,
        contradiction: AssumptionResult,
    ) -> LogicResult:
        """모순이 난 가정을 원본 상태의 X로 바꾸고 기본 로직을 다시 실행한다."""

        state = LogicState.from_snapshot(snapshot)
        candidate = contradiction.assumption
        state.exclude(candidate)
        reason = contradiction.logic_result.message or "가정 결과가 모순입니다."
        deduction = Deduction(
            technique=Technique.REFUTATION_ELIMINATION,
            exclusions=(candidate,),
            evidence_cells=(candidate,),
            explanation=(
                f"{_cell_name(candidate)}에 고양이를 가정하면 모순입니다. ({reason})"
            ),
        )
        first_step = LogicStep(
            number=1,
            deduction=deduction,
            before=snapshot,
            after=state.snapshot(),
        )
        resumed = solve_logically(self.puzzle, state)
        return LogicResult(
            status=resumed.status,
            initial_state=snapshot,
            final_state=resumed.final_state,
            steps=(first_step, *_renumber_steps(resumed.steps, 2)),
            message=resumed.message,
        )

    def _solve_by_refutation(
        self,
        snapshot: LogicSnapshot,
    ) -> tuple[tuple[RefutationRound, ...], Solution | None, bool]:
        """중첩 없는 귀류법을 반복하고, 결론이 없으면 백트래킹한다."""

        rounds: list[RefutationRound] = []
        current = snapshot
        while True:
            selected_unit, candidates = _select_mrv_unit(current)
            assumptions: list[AssumptionResult] = []
            restart = False

            for candidate in candidates:
                result = self._assume_and_propagate(current, candidate)
                assumptions.append(result)

                if result.status is LogicStatus.CONTRADICTION:
                    elimination = self._apply_contradiction(
                        current,
                        result,
                    )
                    rounds.append(
                        RefutationRound(
                            before=current,
                            selected_unit=selected_unit,
                            candidates=candidates,
                            assumptions=tuple(assumptions),
                            elimination=elimination,
                        )
                    )
                    if elimination.status is LogicStatus.SOLVED_LOGICALLY:
                        return (
                            tuple(rounds),
                            _solution_from(elimination.final_state),
                            False,
                        )
                    if elimination.status is LogicStatus.CONTRADICTION:
                        return tuple(rounds), None, False
                    current = elimination.final_state
                    restart = True
                    break

                if result.status is LogicStatus.SOLVED_LOGICALLY:
                    rounds.append(
                        RefutationRound(
                            before=current,
                            selected_unit=selected_unit,
                            candidates=candidates,
                            assumptions=tuple(assumptions),
                        )
                    )
                    return (
                        tuple(rounds),
                        _solution_from(result.logic_result.final_state),
                        False,
                    )

            if restart:
                continue

            rounds.append(
                RefutationRound(
                    before=current,
                    selected_unit=selected_unit,
                    candidates=candidates,
                    assumptions=tuple(assumptions),
                )
            )
            return tuple(rounds), self._backtrack(current), True

    def _backtrack(self, snapshot: LogicSnapshot) -> Solution | None:
        """귀류법 기록을 만들지 않고 첫 해 하나만 찾는다."""

        _, candidates = _select_mrv_unit(snapshot)
        for candidate in candidates:
            result = self._assume_and_propagate(snapshot, candidate)
            if result.status is LogicStatus.SOLVED_LOGICALLY:
                return _solution_from(result.logic_result.final_state)
            if result.status is LogicStatus.STALLED:
                solution = self._backtrack(result.logic_result.final_state)
                if solution is not None:
                    return solution
        return None

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
                "기본 로직 완성과 exact 유일해 판정이 일치하지 않습니다."
            )


def solve(puzzle: Puzzle) -> SolveResult:
    """퍼즐 하나를 풀고 해의 개수를 검증한다."""

    return Solver(puzzle).solve()

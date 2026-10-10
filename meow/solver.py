"""결정적 추론, 한 단계 가정, 분기 탐색을 순서대로 실행하는 풀이 코어.

Exact verifier는 해의 개수만 독립적으로 판정한다. 실제 풀이는 exact가
찾은 좌표를 읽지 않고, 마지막에 해의 존재 여부만 교차 검증한다.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from itertools import combinations

from .exact_solver import ExactResult, ExactStatus, Solution, verify_exact
from .logic_solver import solve_logically
from .model import Cell, Puzzle
from .solve_types import (
    Deduction,
    LogicResult,
    LogicStatus,
    LogicStep,
    Technique,
)
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
class _ProbeCandidateScore:
    """CAT 가정 직후 생기는 직접적인 압력을 나타낸다."""

    cell: Cell
    forced_cats: tuple[Cell, ...]
    new_pair_units: int

    @property
    def forced_cat_count(self) -> int:
        return len(self.forced_cats)

    @property
    def rank_key(self) -> tuple[int, int, int, int]:
        return (
            -self.forced_cat_count,
            -self.new_pair_units,
            self.cell[0],
            self.cell[1],
        )


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


def _cell_name(cell: Cell) -> str:
    return f"R{cell[0] + 1}C{cell[1] + 1}"


def _solution_from(snapshot: LogicSnapshot) -> Solution:
    if not snapshot.is_solved():
        raise RuntimeError("완성되지 않은 상태를 해로 반환할 수 없습니다.")
    return tuple(sorted(snapshot.cats))


def _select_mrv_candidates(snapshot: LogicSnapshot) -> tuple[Cell, ...]:
    """행·열·영역 전체에서 후보가 가장 적은 미완성 단위를 고른다."""

    candidates = min(
        (
            tuple(sorted(snapshot.candidates_for(unit)))
            for unit in snapshot.puzzle.units
            if not snapshot.cats_in(unit)
        ),
        key=len,
        default=None,
    )
    if candidates is None:
        raise RuntimeError("미완성 상태에 MRV로 선택할 단위가 없습니다.")
    if not candidates:
        raise RuntimeError("모순 상태가 결정적 추론을 통과했습니다.")
    return candidates


def _rank_probe_candidates(
    snapshot: LogicSnapshot,
) -> tuple[_ProbeCandidateScore, ...]:
    """직접 제거로 새 CAT을 만드는 후보만 강한 압력 순으로 정렬한다.

    후보를 CAT으로 놓았을 때 생기는 충돌 제거만 가상으로 반영한다. 그
    결과 다른 미완성 단위의 후보가 하나가 되면 새로 강제되는 CAT으로,
    후보가 셋 이상에서 둘이 되면 새 2후보 단위로 센다. 같은 칸이 여러
    단위에서 동시에 강제되어도 CAT은 한 번만 센다.
    """

    active_domains = tuple(
        frozenset(snapshot.candidates_for(unit))
        for unit in snapshot.puzzle.units
        if not snapshot.cats_in(unit)
    )
    scores: list[_ProbeCandidateScore] = []
    for candidate in snapshot.possible_cells:
        conflicts = snapshot.puzzle.conflicts[candidate]
        forced_cats: set[Cell] = set()
        new_pair_units = 0

        for domain in active_domains:
            # 이 가정으로 충족되는 행·열·영역은 후속 압력에서 제외한다.
            if candidate in domain:
                continue
            remaining = domain - conflicts
            if not remaining:
                raise RuntimeError(
                    "결정적 고정점에 단위를 즉시 비우는 CAT 후보가 남았습니다."
                )
            if len(domain) > 1 and len(remaining) == 1:
                forced_cats.update(remaining)
            elif len(domain) > 2 and len(remaining) == 2:
                new_pair_units += 1

        if forced_cats:
            scores.append(
                _ProbeCandidateScore(
                    cell=candidate,
                    forced_cats=tuple(sorted(forced_cats)),
                    new_pair_units=new_pair_units,
                )
            )

    return tuple(sorted(scores, key=lambda score: score.rank_key))


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
    """해를 분류한 뒤 결정적 추론, 한 단계 가정, 분기 탐색을 실행한다."""

    def __init__(self, puzzle: Puzzle) -> None:
        if not isinstance(puzzle, Puzzle):
            raise TypeError("Solver는 Puzzle을 필요로 합니다.")
        self.puzzle = puzzle

    def solve(self) -> SolveResult:
        """첫 유효 해 또는 해 없음을 반환한다."""

        exact_result = verify_exact(self.puzzle)
        initial_logic = solve_logically(self.puzzle)
        rounds: tuple[ProbingRound, ...] = ()
        used_backtrack_search = False

        if initial_logic.status is LogicStatus.SOLVED_LOGICALLY:
            outcome = SolveOutcome.SOLVED_WITH_LOGIC
            solution = _solution_from(initial_logic.final_state)
        elif initial_logic.status is LogicStatus.CONTRADICTION:
            outcome = SolveOutcome.UNSOLVABLE
            solution = None
        else:
            rounds, solution, used_backtrack_search = self._solve_by_probing(
                initial_logic.final_state
            )
            if solution is None:
                outcome = SolveOutcome.UNSOLVABLE
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

    def _probe_candidate(
        self,
        snapshot: LogicSnapshot,
        candidate: Cell,
    ) -> ProbeResult:
        """후보 하나를 고양이로 가정하고 결정적 추론을 고정점까지 실행한다."""

        assumed = LogicState.from_snapshot(snapshot)
        assumed.place_cat(candidate)
        # 이 함수는 solve_logically()만 호출하므로 가정 안에서 다시
        # singleton probing이나 backtrack search로 들어갈 수 없다.
        logic_result = solve_logically(self.puzzle, assumed)
        return ProbeResult(
            assumption=candidate,
            logic_result=logic_result,
        )

    def _apply_refuted_probe(
        self,
        snapshot: LogicSnapshot,
        contradiction: ProbeResult,
    ) -> LogicResult:
        """모순이 난 가정을 원본 상태의 X로 바꾸고 결정적 추론을 다시 실행한다."""

        state = LogicState.from_snapshot(snapshot)
        candidate = contradiction.assumption
        state.exclude(candidate)
        reason = contradiction.logic_result.message or "가정 결과가 모순입니다."
        deduction = Deduction(
            technique=Technique.PROBE_ELIMINATION,
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

    def _solve_by_probing(
        self,
        snapshot: LogicSnapshot,
    ) -> tuple[tuple[ProbingRound, ...], Solution | None, bool]:
        """한 단계 가정을 반복하고, 결론이 없으면 분기 탐색한다."""

        rounds: list[ProbingRound] = []
        current = snapshot
        while True:
            candidates = tuple(score.cell for score in _rank_probe_candidates(current))
            probes: list[ProbeResult] = []
            elimination = None

            for candidate in candidates:
                result = self._probe_candidate(current, candidate)
                probes.append(result)

                if result.status is LogicStatus.CONTRADICTION:
                    elimination = self._apply_refuted_probe(current, result)
                    break
                if result.status is LogicStatus.SOLVED_LOGICALLY:
                    break

            rounds.append(
                ProbingRound(
                    before=current,
                    candidates=candidates,
                    probes=tuple(probes),
                    elimination=elimination,
                )
            )
            if elimination is not None:
                if elimination.status is LogicStatus.SOLVED_LOGICALLY:
                    return tuple(rounds), _solution_from(elimination.final_state), False
                if elimination.status is LogicStatus.CONTRADICTION:
                    return tuple(rounds), None, False
                current = elimination.final_state
            elif probes and probes[-1].status is LogicStatus.SOLVED_LOGICALLY:
                return (
                    tuple(rounds),
                    _solution_from(probes[-1].logic_result.final_state),
                    False,
                )
            else:
                return tuple(rounds), self._backtrack_search(current), True

    def _backtrack_search(self, snapshot: LogicSnapshot) -> Solution | None:
        """추가 재생 기록을 만들지 않고 분기하여 첫 해 하나만 찾는다."""

        candidates = _select_mrv_candidates(snapshot)
        for candidate in candidates:
            result = self._probe_candidate(snapshot, candidate)
            if result.status is LogicStatus.SOLVED_LOGICALLY:
                return _solution_from(result.logic_result.final_state)
            if result.status is LogicStatus.STALLED:
                solution = self._backtrack_search(result.logic_result.final_state)
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
                "결정적 추론 완성과 exact 유일해 판정이 일치하지 않습니다."
            )


def solve(puzzle: Puzzle) -> SolveResult:
    """퍼즐 하나를 풀고 해의 개수를 검증한다."""

    return Solver(puzzle).solve()

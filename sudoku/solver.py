"""Human-style Sudoku reasoning with a complete-search safety net."""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Final

from .board import Grid, Puzzle
from .solve_types import (
    Assignment,
    CandidateGrid,
    ContradictionKind,
    ContradictionWitness,
    Elimination,
    SolveResult,
    SolveStatus,
    SolveStep,
    StepKind,
    Technique,
    TechniqueResult,
)
from .solver_state import SolverState
from .techniques import find_next_deduction
from .topology import COLS, PEERS, ROWS, UNITS, Cell

_SOLUTION_LIMIT: Final = 2
type _StateSnapshot = tuple[Grid, CandidateGrid]


class _ProbeOutcome(Enum):
    REFUTED = auto()
    SOLVED = auto()
    STALLED = auto()


@dataclass(frozen=True, slots=True)
class _ProbeResult:
    outcome: _ProbeOutcome
    solution: _StateSnapshot | None = None


@dataclass(slots=True)
class _ProbeHistory:
    """Remember stalled assumptions only while one solve is in progress."""

    stalled: dict[Assignment, tuple[int, int]] = field(default_factory=dict)
    next_serial: int = 0

    def refresh_scores(self, scored: tuple[tuple[Assignment, int], ...]) -> None:
        for decision, h1 in scored:
            previous = self.stalled.get(decision)
            if previous is not None and previous[0] != h1:
                del self.stalled[decision]

    def priority(self, decision: Assignment, h1: int) -> tuple[int, int]:
        previous = self.stalled.get(decision)
        if previous is None:
            return 0, 0
        if previous[0] != h1:
            raise RuntimeError("갱신되지 않은 H1 점수 이력입니다.")
        return 1, previous[1]

    def remember_stall(self, decision: Assignment, h1: int) -> None:
        self.stalled[decision] = h1, self.next_serial
        self.next_serial += 1


def _direct_h1(
    grid: Grid,
    candidates: CandidateGrid,
    decision: Assignment,
) -> int:
    """Count constraints made single by applying one assumption directly."""

    cell = decision.cell
    value = decision.value
    row, col = cell
    if grid[row][col] != 0 or value not in candidates[row][col]:
        raise RuntimeError("현재 후보가 아닌 값을 H1 점수로 계산할 수 없습니다.")

    affected_peers = {
        peer
        for peer in PEERS[cell]
        if grid[peer[0]][peer[1]] == 0 and value in candidates[peer[0]][peer[1]]
    }
    h1 = sum(len(candidates[peer[0]][peer[1]]) == 2 for peer in affected_peers)

    other_values = candidates[row][col] - {value}
    for unit in UNITS:
        if cell in unit:
            for other_value in other_values:
                before = sum(
                    grid[unit_row][unit_col] == 0
                    and other_value in candidates[unit_row][unit_col]
                    for unit_row, unit_col in unit
                )
                h1 += int(before == 2)
            continue

        removed = sum(peer in affected_peers for peer in unit)
        if not removed:
            continue
        before = sum(
            grid[unit_row][unit_col] == 0 and value in candidates[unit_row][unit_col]
            for unit_row, unit_col in unit
        )
        h1 += int(before > 1 and before - removed == 1)

    return h1


class SudokuSolver:
    """Explain logic and bivalue one-ply refutations, then find up to two solutions."""

    __slots__ = ("_puzzle",)

    def __init__(self, puzzle: Puzzle):
        if not isinstance(puzzle, Puzzle):
            raise TypeError("SudokuSolver는 Puzzle을 받아야 합니다.")
        self._puzzle = puzzle

    def solve(self) -> SolveResult:
        """Solve the puzzle and distinguish zero, one, or multiple solutions.

        The visible trace permits at most one active assumption. At a logical
        fixed point, candidates from every two-candidate cell are ranked by the
        number of constraints made single by applying them directly. Equal
        scores rotate previously stalled assumptions behind fresh ones, then
        fall back to row-major cell and ascending value order. A contradictory
        candidate is removed and normal logic resumes. A completed branch
        supplies a valid representative solution; the later silent search
        still checks whether another solution exists. If every branch stalls,
        recursive MRV search runs silently and the trace marks the exact point
        where the human-readable explanation ended.
        """

        steps: list[SolveStep] = []

        state = SolverState(self._puzzle)
        steps.append(
            self._step_from_state(
                StepKind.INITIAL_STATE,
                state,
                message="초기 후보 상태",
            )
        )

        preferred_solution = self._run_human_reasoning(state, steps)
        search_required = (
            preferred_solution is None
            and not state.is_complete()
            and state.find_contradiction() is None
        )
        if search_required:
            steps.append(
                self._step_from_state(
                    StepKind.SEARCH_FALLBACK,
                    state,
                    message=(
                        "2후보 셀이 없거나 모든 2후보 가정이 정체되어, "
                        "여기부터는 MRV 백트래킹으로 전환합니다."
                    ),
                )
            )

        solutions: list[_StateSnapshot] = []
        if preferred_solution is not None:
            solutions.append(preferred_solution)
        self._collect_solutions(state.clone(), solutions)

        if not solutions:
            status = SolveStatus.UNSOLVABLE
            steps.append(
                self._step_from_state(
                    StepKind.UNSOLVABLE,
                    state,
                    message="현재 단서로 가능한 해가 없습니다.",
                )
            )
        else:
            status = (
                SolveStatus.SOLVED_MULTIPLE
                if len(solutions) >= _SOLUTION_LIMIT
                else SolveStatus.SOLVED_UNIQUE
            )
            solution, solution_candidates = solutions[0]

            terminal_message = (
                "해가 둘 이상 존재합니다. 표시한 보드는 가능한 해 중 하나입니다."
                if status is SolveStatus.SOLVED_MULTIPLE
                else "유일한 해를 확인했습니다."
            )
            steps.append(
                SolveStep(
                    kind=StepKind.SOLVED,
                    grid=solution,
                    candidates=solution_candidates,
                    message=terminal_message,
                )
            )

        return SolveResult(
            status=status,
            steps=tuple(steps),
        )

    def _run_human_reasoning(
        self,
        state: SolverState,
        steps: list[SolveStep],
    ) -> _StateSnapshot | None:
        """Run fixed-point logic and sequential, non-nested bivalue probes."""

        probe_history = _ProbeHistory()
        while True:
            if not self._propagate_logic(state, assumption=None, steps=steps):
                return None
            if state.is_complete():
                return self._snapshot(state)

            probe_result = self._probe_bivalue_candidates(
                state,
                steps,
                probe_history,
            )
            if probe_result.outcome is _ProbeOutcome.SOLVED:
                if probe_result.solution is None:
                    raise RuntimeError("완성된 가정 결과에 해가 없습니다.")
                return probe_result.solution
            if probe_result.outcome is _ProbeOutcome.STALLED:
                return None

    def _probe_bivalue_candidates(
        self,
        state: SolverState,
        steps: list[SolveStep],
        history: _ProbeHistory,
    ) -> _ProbeResult:
        """Try every current bivalue assumption in H1 order until one is decisive."""

        grid = state.to_grid()
        candidates = state.candidate_grid()
        bivalue_cells = tuple(
            cell
            for cell in state.empty_cells()
            if len(candidates[cell[0]][cell[1]]) == 2
        )
        scored = tuple(
            (decision, _direct_h1(grid, candidates, decision))
            for cell in bivalue_cells
            for decision in (
                Assignment(cell, value)
                for value in sorted(candidates[cell[0]][cell[1]])
            )
        )
        history.refresh_scores(scored)
        ordered = sorted(
            scored,
            key=lambda item: (
                -item[1],
                *history.priority(*item),
                item[0].cell,
                item[0].value,
            ),
        )

        for decision, h1 in ordered:
            result = self._probe_candidate(state, decision, steps)
            if result.outcome is _ProbeOutcome.STALLED:
                history.remember_stall(decision, h1)
                continue
            return result
        return _ProbeResult(_ProbeOutcome.STALLED)

    def _probe_candidate(
        self,
        state: SolverState,
        decision: Assignment,
        steps: list[SolveStep],
    ) -> _ProbeResult:
        """Run ordinary logic under one assumption without nesting probes."""

        row, col = decision.cell
        value = decision.value
        branch = state.clone()
        if not branch.set_value(decision.cell, value):
            raise RuntimeError("현재 2후보 셀의 후보를 가정 상태에 적용할 수 없습니다.")

        steps.append(
            self._step_from_state(
                StepKind.ASSUMPTION,
                branch,
                assumption=decision,
                message=(
                    f"2후보 셀 가정: R{row + 1}C{col + 1} = {value}로 두고 "
                    "추가 가정 없이 기존 논리만 적용합니다."
                ),
            )
        )

        if not self._propagate_logic(
            branch,
            assumption=decision,
            steps=steps,
        ):
            removed = state.remove_candidates(decision.cell, {value})
            if removed != frozenset({value}):
                raise RuntimeError(
                    "모순이 증명된 후보를 원래 상태에서 제거할 수 없습니다."
                )

            deduction = TechniqueResult(
                technique=Technique.REFUTATION,
                eliminations=(Elimination(decision.cell, removed),),
                evidence_cells=(decision.cell,),
                explanation="이 후보를 참이라고 가정하면 모순이 발생합니다.",
            )
            steps.append(
                self._step_from_state(
                    StepKind.REFUTATION,
                    state,
                    deduction=deduction,
                    assumption=decision,
                )
            )
            return _ProbeResult(_ProbeOutcome.REFUTED)

        if branch.is_complete():
            steps.append(
                self._step_from_state(
                    StepKind.ASSUMPTION_SOLVED,
                    branch,
                    assumption=decision,
                    message=(
                        f"R{row + 1}C{col + 1} = {value} 가정에서 "
                        "추가 가정 없이 해 하나를 완성했습니다."
                    ),
                )
            )
            return _ProbeResult(
                _ProbeOutcome.SOLVED,
                solution=self._snapshot(branch),
            )

        steps.append(
            self._step_from_state(
                StepKind.ASSUMPTION_STALLED,
                branch,
                assumption=decision,
                message=(
                    f"R{row + 1}C{col + 1} = {value} 가정에서는 "
                    "모순도 완성도 나오지 않아 원래 상태로 돌아갑니다."
                ),
            )
        )
        return _ProbeResult(_ProbeOutcome.STALLED)

    def _collect_solutions(
        self,
        state: SolverState,
        solutions: list[_StateSnapshot],
    ) -> None:
        """Recursively collect distinct solutions without adding trace steps."""

        if len(solutions) >= _SOLUTION_LIMIT:
            return
        if not self._propagate_logic(state, assumption=None, steps=None):
            return

        if state.is_complete():
            snapshot = self._snapshot(state)
            if all(existing_grid != snapshot[0] for existing_grid, _ in solutions):
                solutions.append(snapshot)
            return

        cell = self._mrv_cell(state)
        for value in sorted(state.candidates_at(cell)):
            if len(solutions) >= _SOLUTION_LIMIT:
                return
            branch = state.clone()
            if branch.set_value(cell, value):
                self._collect_solutions(branch, solutions)

    def _propagate_logic(
        self,
        state: SolverState,
        *,
        assumption: Assignment | None,
        steps: list[SolveStep] | None,
    ) -> bool:
        """Apply supported logical deductions to a fixed point or contradiction."""

        while True:
            contradiction = state.find_contradiction()
            if contradiction is not None:
                if steps is not None:
                    steps.append(
                        self._step_from_state(
                            StepKind.CONTRADICTION,
                            state,
                            assumption=assumption,
                            contradiction=contradiction,
                            message=self._contradiction_message(contradiction),
                        )
                    )
                return False

            deduction = find_next_deduction(
                state.to_grid(),
                state.candidate_grid(),
            )
            if deduction is None:
                return True

            self._apply_deduction(state, deduction)
            if steps is not None:
                steps.append(
                    self._step_from_state(
                        StepKind.TECHNIQUE,
                        state,
                        deduction=deduction,
                        assumption=assumption,
                    )
                )

    @staticmethod
    def _mrv_cell(state: SolverState) -> Cell:
        empty_cells = state.empty_cells()
        if not empty_cells:
            raise RuntimeError("완성된 상태에서는 MRV 셀을 선택할 수 없습니다.")
        return min(
            empty_cells,
            key=lambda cell: (len(state.candidates_at(cell)), cell),
        )

    @staticmethod
    def _snapshot(state: SolverState) -> _StateSnapshot:
        return state.to_grid(), state.candidate_grid()

    @staticmethod
    def _apply_deduction(state: SolverState, result: TechniqueResult) -> None:
        """Apply one logical wave previously computed from the unchanged state."""

        if not result.has_changes:
            raise RuntimeError("변경이 없는 논리 기법 결과는 적용할 수 없습니다.")

        for elimination in result.eliminations:
            removed = state.remove_candidates(elimination.cell, elimination.values)
            if removed != elimination.values:
                raise RuntimeError("기법 결과가 현재 후보 상태와 일치하지 않습니다.")

        for assignment in result.assignments:
            if not state.set_value(assignment.cell, assignment.value):
                raise RuntimeError(
                    "기법이 현재 상태에 적용할 수 없는 값을 배치했습니다."
                )

    @classmethod
    def _contradiction_message(cls, witness: ContradictionWitness) -> str:
        if witness.kind is ContradictionKind.EMPTY_CELL and len(witness.cells) == 1:
            cell = witness.cells[0]
            return (
                "모순을 발견했습니다. "
                f"R{cell[0] + 1}C{cell[1] + 1}에 남은 후보가 없습니다."
            )

        if (
            witness.kind is ContradictionKind.MISSING_DIGIT
            and witness.unit_index is not None
            and len(witness.digits) == 1
        ):
            unit_name = cls._unit_name(witness.unit_index)
            value = min(witness.digits)
            return f"모순을 발견했습니다. {unit_name}에 숫자 {value}가 들어갈 곳이 없습니다."

        raise RuntimeError("구조가 잘못된 모순 witness입니다.")

    @staticmethod
    def _unit_name(unit_index: int) -> str:
        if unit_index < len(ROWS):
            return f"{unit_index + 1}행"
        if unit_index < len(ROWS) + len(COLS):
            return f"{unit_index - len(ROWS) + 1}열"
        return f"{unit_index - len(ROWS) - len(COLS) + 1}번 박스"

    @staticmethod
    def _step_from_state(
        kind: StepKind,
        state: SolverState,
        *,
        deduction: TechniqueResult | None = None,
        assumption: Assignment | None = None,
        contradiction: ContradictionWitness | None = None,
        message: str = "",
    ) -> SolveStep:
        return SolveStep(
            kind=kind,
            grid=state.to_grid(),
            candidates=state.candidate_grid(),
            deduction=deduction,
            assumption=assumption,
            contradiction=contradiction,
            message=message,
        )

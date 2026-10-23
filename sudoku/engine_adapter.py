"""Sudoku rules and branch ordering for the shared solving engine."""

from dataclasses import dataclass, field

from .board import Grid
from .solve_types import (
    Assignment,
    CandidateGrid,
    ContradictionWitness,
    Elimination,
    Technique,
    TechniqueResult,
)
from .solver_state import SolverState
from .techniques import find_next_deduction
from .topology import CELLS, PEERS, UNITS

type SudokuSnapshot = tuple[Grid, CandidateGrid]


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


class SudokuDomain:
    """Keep Sudoku deductions and H1 ranking separate from execution."""

    def __init__(self) -> None:
        self._history = _ProbeHistory()
        self._scores: dict[Assignment, int] = {}

    @staticmethod
    def find_deduction(snapshot: SudokuSnapshot) -> TechniqueResult | None:
        return find_next_deduction(*snapshot)

    @staticmethod
    def apply_deduction(state: SolverState, result: TechniqueResult) -> None:
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

    def probe_candidates(self, snapshot: SudokuSnapshot) -> tuple[Assignment, ...]:
        grid, candidates = snapshot
        scored = tuple(
            (decision, _direct_h1(grid, candidates, decision))
            for row, col in CELLS
            if grid[row][col] == 0 and len(candidates[row][col]) == 2
            for decision in (
                Assignment((row, col), value) for value in sorted(candidates[row][col])
            )
        )
        self._history.refresh_scores(scored)
        self._scores = dict(scored)
        return tuple(
            decision
            for decision, _ in sorted(
                scored,
                key=lambda item: (
                    -item[1],
                    *self._history.priority(*item),
                    item[0].cell,
                    item[0].value,
                ),
            )
        )

    def probe_stalled(self, decision: Assignment) -> None:
        self._history.remember_stall(decision, self._scores[decision])

    @staticmethod
    def assume(state: SolverState, decision: Assignment) -> None:
        if not state.set_value(decision.cell, decision.value):
            raise RuntimeError("현재 후보를 가정 상태에 적용할 수 없습니다.")

    @staticmethod
    def refutation(
        decision: Assignment, witness: ContradictionWitness
    ) -> TechniqueResult:
        return TechniqueResult(
            technique=Technique.REFUTATION,
            eliminations=(Elimination(decision.cell, frozenset({decision.value})),),
            evidence_cells=(decision.cell,),
            explanation="이 후보를 참이라고 가정하면 모순이 발생합니다.",
        )

    @staticmethod
    def search_candidates(snapshot: SudokuSnapshot) -> tuple[Assignment, ...]:
        grid, candidates = snapshot
        empty_cells = tuple(cell for cell in CELLS if grid[cell[0]][cell[1]] == 0)
        if not empty_cells:
            raise RuntimeError("완성된 상태에서는 MRV 셀을 선택할 수 없습니다.")
        cell = min(
            empty_cells, key=lambda cell: (len(candidates[cell[0]][cell[1]]), cell)
        )
        return tuple(
            Assignment(cell, value) for value in sorted(candidates[cell[0]][cell[1]])
        )

    @staticmethod
    def solution_key(snapshot: SudokuSnapshot) -> Grid:
        return snapshot[0]

"""MEOW rules and state deltas for the shared solving engine."""

from __future__ import annotations

from dataclasses import dataclass

from puzzle_common.coordinates import cell_name as _cell_name

from .model import Cell
from .solve_types import Deduction, Technique
from .state import LogicSnapshot, LogicState
from .techniques import find_next_deduction


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


class MeowDomain:
    """Supply MEOW deductions, decisions, and state deltas to the engine."""

    def find_deduction(self, snapshot: LogicSnapshot) -> Deduction | None:
        return find_next_deduction(snapshot)

    def apply_deduction(self, state: LogicState, deduction: Deduction) -> None:
        changed = False
        for cell in deduction.placements:
            changed = state.place_cat(cell) or changed
        for cell in deduction.exclusions:
            changed = state.exclude(cell) or changed
        if not changed:
            raise RuntimeError("finder가 상태를 바꾸지 않는 추론을 반환했습니다.")

    def probe_candidates(self, snapshot: LogicSnapshot) -> tuple[Cell, ...]:
        return tuple(score.cell for score in _rank_probe_candidates(snapshot))

    def probe_stalled(self, decision: Cell) -> None:
        pass

    def assume(self, state: LogicState, decision: Cell) -> None:
        state.place_cat(decision)

    def refutation(self, decision: Cell, witness: str) -> Deduction:
        reason = witness or "가정 결과가 모순입니다."
        return Deduction(
            technique=Technique.PROBE_ELIMINATION,
            exclusions=(decision,),
            evidence_cells=(decision,),
            explanation=(
                f"{_cell_name(decision)}에 고양이를 가정하면 모순입니다. ({reason})"
            ),
        )

    def search_candidates(self, snapshot: LogicSnapshot) -> tuple[Cell, ...]:
        return _select_mrv_candidates(snapshot)

    def solution_key(self, snapshot: LogicSnapshot) -> tuple[Cell, ...]:
        return tuple(sorted(snapshot.cats))

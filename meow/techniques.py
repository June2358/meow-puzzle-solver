"""상태를 변경하지 않는 결정적 추론 finder 모음.

각 finder는 현재 snapshot에서 안정적인 순서로 첫 번째 추론만 반환한다.
후보를 실제로 지우거나 고양이를 놓는 일은 :mod:`meow.solver`만 한다.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from itertools import combinations
from typing import Final

from puzzle_common.constraints import locked_candidate_targets
from puzzle_common.coordinates import cell_name as _cell_name

from .model import Cell, Puzzle, Unit
from .solve_types import Deduction, Technique, UnitKind, UnitRef
from .state import LogicSnapshot

TechniqueFinder = Callable[[LogicSnapshot], Deduction | None]


def _kind_name(kind: UnitKind) -> str:
    return {
        UnitKind.ROW: "행",
        UnitKind.COLUMN: "열",
        UnitKind.REGION: "색상 영역",
    }[kind]


def _unit_name(puzzle: Puzzle, ref: UnitRef) -> str:
    if ref.kind is UnitKind.REGION:
        return "표시된 색상 영역"
    return f"{_kind_name(ref.kind)} {ref.index + 1}"


def _unit_group_name(puzzle: Puzzle, refs: tuple[UnitRef, ...]) -> str:
    if refs and refs[0].kind is UnitKind.REGION:
        if len(refs) == 1:
            return "표시된 색상 영역"
        return f"표시된 {len(refs)}개 색상 영역"
    return ", ".join(_unit_name(puzzle, ref) for ref in refs)


def _units(puzzle: Puzzle, kind: UnitKind) -> tuple[Unit, ...]:
    if kind is UnitKind.ROW:
        return puzzle.rows
    if kind is UnitKind.COLUMN:
        return puzzle.cols
    return puzzle.regions


def _unit_index(puzzle: Puzzle, kind: UnitKind, cell: Cell) -> int:
    if kind is UnitKind.ROW:
        return cell[0]
    if kind is UnitKind.COLUMN:
        return cell[1]
    return puzzle.region_of(cell)


def _active_units(
    state: LogicSnapshot, kind: UnitKind
) -> Iterator[tuple[int, Unit, tuple[Cell, ...]]]:
    """Yield unfilled units with candidates in their original order."""

    for index, unit in enumerate(_units(state.puzzle, kind)):
        if state.cats_in(unit):
            continue
        candidates = state.candidates_for(unit)
        if candidates:
            yield index, unit, candidates


def find_placed_cat_elimination(state: LogicSnapshot) -> Deduction | None:
    """이미 놓인 첫 고양이와 충돌하는 모든 현재 후보를 제외한다."""

    puzzle = state.puzzle
    for cat in sorted(state.cats):
        targets = tuple(
            cell for cell in sorted(puzzle.conflicts[cat]) if state.is_possible(cell)
        )
        if not targets:
            continue
        return Deduction(
            technique=Technique.PLACED_CAT_ELIMINATION,
            exclusions=targets,
            evidence_cells=(cat,),
            explanation=(
                f"{_cell_name(cat)}에 고양이가 있으므로, 같은 행·열·색상 "
                "영역 또는 인접한 칸에는 고양이를 놓을 수 없습니다."
            ),
        )
    return None


def _find_single(state: LogicSnapshot, kind: UnitKind) -> Deduction | None:
    puzzle = state.puzzle
    technique = {
        UnitKind.ROW: Technique.ROW_SINGLE,
        UnitKind.COLUMN: Technique.COLUMN_SINGLE,
        UnitKind.REGION: Technique.REGION_SINGLE,
    }[kind]

    for index, _, candidates in _active_units(state, kind):
        if len(candidates) != 1:
            continue
        cell = candidates[0]
        ref = UnitRef(kind, index)
        return Deduction(
            technique=technique,
            placements=(cell,),
            evidence_cells=(cell,),
            evidence_units=(ref,),
            explanation=(
                f"{_unit_name(puzzle, ref)}에서 고양이를 놓을 수 있는 칸은 "
                f"{_cell_name(cell)} 하나뿐입니다. 따라서 "
                f"{_cell_name(cell)}에 고양이를 놓습니다."
            ),
        )
    return None


def find_row_single(state: LogicSnapshot) -> Deduction | None:
    """후보가 하나뿐인 첫 행을 찾는다."""

    return _find_single(state, UnitKind.ROW)


def find_column_single(state: LogicSnapshot) -> Deduction | None:
    """후보가 하나뿐인 첫 열을 찾는다."""

    return _find_single(state, UnitKind.COLUMN)


def find_region_single(state: LogicSnapshot) -> Deduction | None:
    """후보가 하나뿐인 첫 영역을 찾는다."""

    return _find_single(state, UnitKind.REGION)


_LINE_LOCK_SPECS: Final[tuple[tuple[UnitKind, UnitKind, Technique], ...]] = (
    (UnitKind.REGION, UnitKind.ROW, Technique.REGION_TO_ROW_LOCK),
    (UnitKind.REGION, UnitKind.COLUMN, Technique.REGION_TO_COLUMN_LOCK),
    (UnitKind.ROW, UnitKind.REGION, Technique.ROW_TO_REGION_LOCK),
    (UnitKind.COLUMN, UnitKind.REGION, Technique.COLUMN_TO_REGION_LOCK),
)


def find_region_line_lock(state: LogicSnapshot) -> Deduction | None:
    """영역↔행/열 양방향 locked-candidate를 찾는다.

    source 단위의 모든 후보가 target 단위 하나에 있으면 source의 고양이가
    target의 고양이도 겸한다. 따라서 target에서 source 밖 후보는 불가능하다.
    """

    puzzle = state.puzzle
    for source_kind, target_kind, technique in _LINE_LOCK_SPECS:
        for source_index, source, candidates in _active_units(state, source_kind):
            locked = locked_candidate_targets(
                frozenset(source),
                candidates,
                _units(puzzle, target_kind),
                lambda cell, kind=target_kind: _unit_index(puzzle, kind, cell),
                state.is_possible,
            )
            if locked is None:
                continue
            target_index, exclusions = locked
            source_ref = UnitRef(source_kind, source_index)
            target_ref = UnitRef(target_kind, target_index)
            return Deduction(
                technique=technique,
                exclusions=exclusions,
                evidence_cells=candidates,
                evidence_units=(source_ref, target_ref),
                explanation=(
                    f"{_unit_name(puzzle, source_ref)}의 남은 후보가 모두 "
                    f"{_unit_name(puzzle, target_ref)}에 있습니다. 따라서 "
                    f"{_unit_name(puzzle, target_ref)}의 고양이는 "
                    f"{_unit_name(puzzle, source_ref)}에 있어야 하므로, "
                    "다른 후보를 제외합니다."
                ),
            )
    return None


_UNIT_SUPPORT_SOURCE_ORDER: Final[tuple[UnitKind, ...]] = (
    UnitKind.REGION,
    UnitKind.ROW,
    UnitKind.COLUMN,
)


def find_unit_support(state: LogicSnapshot) -> Deduction | None:
    """한 exact-one 단위의 모든 후보와 충돌하는 칸을 제외한다.

    단위에는 반드시 고양이가 하나 있어야 하므로, 그 고양이의 어느 후보와도
    공존할 수 없는 칸은 고양이가 될 수 없다. 도미노나 L자 같은 모양별 규칙을
    따로 하드코딩하지 않고 충돌 집합의 교집합으로 처리한다.
    """

    puzzle = state.puzzle
    possible_cells = frozenset(state.possible_cells)
    for kind in _UNIT_SUPPORT_SOURCE_ORDER:
        for index, _, candidates in _active_units(state, kind):
            common_conflicts = possible_cells.intersection(
                *(puzzle.conflicts[cell] for cell in candidates)
            )
            exclusions = tuple(sorted(common_conflicts))
            if not exclusions:
                continue

            source_ref = UnitRef(kind, index)
            source_name = _unit_name(puzzle, source_ref)
            if len(exclusions) == 1:
                target_name = _cell_name(exclusions[0])
                explanation = (
                    f"{target_name}에 고양이를 놓으면 {source_name}의 남은 "
                    f"후보가 모두 막힙니다. {source_name}에는 반드시 고양이 "
                    f"하나가 필요하므로 {target_name}는 X입니다."
                )
            else:
                explanation = (
                    f"표시된 각 대상 칸에 고양이를 놓으면 {source_name}의 "
                    f"남은 후보가 모두 막힙니다. {source_name}에는 반드시 "
                    "고양이 하나가 필요하므로 이 칸들을 X로 표시합니다."
                )
            return Deduction(
                technique=Technique.UNIT_SUPPORT,
                exclusions=exclusions,
                evidence_cells=candidates,
                evidence_units=(source_ref,),
                explanation=explanation,
            )
    return None


_HALL_KIND_PAIRS: Final[tuple[tuple[UnitKind, UnitKind], ...]] = (
    (UnitKind.ROW, UnitKind.COLUMN),
    (UnitKind.COLUMN, UnitKind.ROW),
    (UnitKind.REGION, UnitKind.ROW),
    (UnitKind.ROW, UnitKind.REGION),
    (UnitKind.REGION, UnitKind.COLUMN),
    (UnitKind.COLUMN, UnitKind.REGION),
)
_MAX_HALL_SIZE: Final = 3


def _hall_exclusions(
    state: LogicSnapshot,
    source_kind: UnitKind,
    target_kind: UnitKind,
    source_indices: tuple[int, ...],
    target_indices: frozenset[int],
) -> tuple[Cell, ...]:
    """예약된 target 단위에서 선택된 source 밖 후보를 반환한다."""

    puzzle = state.puzzle
    selected_sources = frozenset(source_indices)
    cells: set[Cell] = set()
    target_units = _units(puzzle, target_kind)
    for target_index in target_indices:
        for cell in target_units[target_index]:
            if not state.is_possible(cell):
                continue
            if _unit_index(puzzle, source_kind, cell) in selected_sources:
                continue
            cells.add(cell)
    return tuple(sorted(cells))


def find_hall_lock(state: LogicSnapshot) -> Deduction | None:
    """행·열·영역 파티션 사이의 첫 Hall lock을 찾는다.

    k개의 source 단위 후보가 정확히 k개의 target 단위에만 걸쳐 있으면, 그
    target 단위들은 source 고양이들이 전부 차지한다. target의 나머지 후보를
    제외한다. 조합 폭발을 피하기 위해 3개 단위까지 검사하고, 그보다 큰
    조합이 필요한 상태는 한 단계 가정이나 분기 탐색으로 넘긴다.
    """

    puzzle = state.puzzle
    for source_kind, target_kind in _HALL_KIND_PAIRS:
        active: list[tuple[int, tuple[Cell, ...], frozenset[int]]] = []
        for source_index, _, candidates in _active_units(state, source_kind):
            targets = frozenset(
                _unit_index(puzzle, target_kind, cell) for cell in candidates
            )
            if len(targets) > _MAX_HALL_SIZE:
                continue
            active.append((source_index, candidates, targets))

        max_subset_size = min(len(active), _MAX_HALL_SIZE)
        for subset_size in range(2, max_subset_size + 1):
            for subset in combinations(active, subset_size):
                target_indices = frozenset(
                    target_index for _, _, targets in subset for target_index in targets
                )
                if len(target_indices) != subset_size:
                    continue

                source_indices = tuple(item[0] for item in subset)
                exclusions = _hall_exclusions(
                    state,
                    source_kind,
                    target_kind,
                    source_indices,
                    target_indices,
                )
                if not exclusions:
                    continue

                source_refs = tuple(
                    UnitRef(source_kind, index) for index in source_indices
                )
                target_refs = tuple(
                    UnitRef(target_kind, index) for index in sorted(target_indices)
                )
                evidence = tuple(
                    sorted({cell for _, candidates, _ in subset for cell in candidates})
                )
                return Deduction(
                    technique=Technique.HALL_LOCK,
                    exclusions=exclusions,
                    evidence_cells=evidence,
                    evidence_units=(*source_refs, *target_refs),
                    explanation=(
                        f"{_unit_group_name(puzzle, source_refs)}의 남은 후보가 "
                        f"{_unit_group_name(puzzle, target_refs)}에만 있습니다. "
                        f"이 단위들에는 고양이 {subset_size}마리가 필요하므로 "
                        f"{_unit_group_name(puzzle, target_refs)}은 이 고양이들이 "
                        "차지합니다. 따라서 다른 후보를 제외합니다."
                    ),
                )
    return None


DIRECT_PROPAGATION_FINDERS: Final[tuple[TechniqueFinder, ...]] = (
    find_placed_cat_elimination,
    find_row_single,
    find_column_single,
    find_region_single,
)

UNIT_SUPPORT_FINDERS: Final[tuple[TechniqueFinder, ...]] = (find_unit_support,)

CONTAINER_MATCHING_FINDERS: Final[tuple[TechniqueFinder, ...]] = (
    find_region_line_lock,
    find_hall_lock,
)

TECHNIQUE_FINDERS: Final[tuple[TechniqueFinder, ...]] = (
    *DIRECT_PROPAGATION_FINDERS,
    *CONTAINER_MATCHING_FINDERS,
    *UNIT_SUPPORT_FINDERS,
)


def find_next_deduction(state: LogicSnapshot) -> Deduction | None:
    """쉬운 기법 우선의 안정적인 순서로 첫 추론을 반환한다."""

    for finder in TECHNIQUE_FINDERS:
        deduction = finder(state)
        if deduction is not None:
            return deduction
    return None

"""상태를 변경하지 않는 결정적 추론 finder 모음.

각 finder는 현재 snapshot에서 안정적인 순서로 첫 번째 추론만 반환한다.
후보를 실제로 지우거나 고양이를 놓는 일은 :mod:`meow.logic_solver`만 한다.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from itertools import combinations
from typing import Final

from .model import Cell, Puzzle, Unit
from .solve_types import Deduction, Technique, UnitKind, UnitRef
from .state import LogicSnapshot

TechniqueFinder = Callable[[LogicSnapshot], Deduction | None]


def _cell_name(cell: Cell) -> str:
    row, column = cell
    return f"R{row + 1}C{column + 1}"


def _kind_name(kind: UnitKind) -> str:
    return {
        UnitKind.ROW: "행",
        UnitKind.COLUMN: "열",
        UnitKind.REGION: "영역",
    }[kind]


def _unit_name(puzzle: Puzzle, ref: UnitRef) -> str:
    if ref.kind is UnitKind.REGION:
        return f"영역 {puzzle.region_labels[ref.index]}"
    return f"{_kind_name(ref.kind)} {ref.index + 1}"


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


def _has_cat(state: LogicSnapshot, unit: Sequence[Cell]) -> bool:
    return any(state.is_cat(cell) for cell in unit)


def _candidates(state: LogicSnapshot, unit: Sequence[Cell]) -> tuple[Cell, ...]:
    return tuple(sorted(state.candidates_for(unit)))


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
                f"{_cell_name(cat)}에 놓인 고양이와 같은 행·열·영역에 "
                "있거나 인접한 후보는 함께 고양이가 될 수 없습니다."
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

    for index, unit in enumerate(_units(puzzle, kind)):
        if _has_cat(state, unit):
            continue
        candidates = _candidates(state, unit)
        if len(candidates) != 1:
            continue
        cell = candidates[0]
        ref = UnitRef(kind, index)
        return Deduction(
            technique=technique,
            placements=(cell,),
            evidence_cells=(cell,),
            explanation=(
                f"{_unit_name(puzzle, ref)}에서 가능한 칸은 "
                f"{_cell_name(cell)} 하나뿐입니다."
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
        for source_index, source in enumerate(_units(puzzle, source_kind)):
            if _has_cat(state, source):
                continue
            candidates = _candidates(state, source)
            if not candidates:
                continue
            target_indices = {
                _unit_index(puzzle, target_kind, cell) for cell in candidates
            }
            if len(target_indices) != 1:
                continue

            target_index = min(target_indices)
            target = _units(puzzle, target_kind)[target_index]
            source_cells = frozenset(source)
            exclusions = tuple(
                cell
                for cell in target
                if cell not in source_cells and state.is_possible(cell)
            )
            if not exclusions:
                continue

            source_ref = UnitRef(source_kind, source_index)
            target_ref = UnitRef(target_kind, target_index)
            return Deduction(
                technique=technique,
                exclusions=exclusions,
                evidence_cells=candidates,
                explanation=(
                    f"{_unit_name(puzzle, source_ref)}의 모든 후보가 "
                    f"{_unit_name(puzzle, target_ref)}에 있으므로 두 단위의 "
                    "고양이는 같은 칸이어야 합니다."
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
    possible_cells = tuple(sorted(state.possible_cells))
    for kind in _UNIT_SUPPORT_SOURCE_ORDER:
        for index, unit in enumerate(_units(puzzle, kind)):
            if _has_cat(state, unit):
                continue
            candidates = _candidates(state, unit)
            if not candidates:
                continue

            exclusions = tuple(
                target
                for target in possible_cells
                if all(
                    target in puzzle.conflicts[candidate] for candidate in candidates
                )
            )
            if not exclusions:
                continue

            source_ref = UnitRef(kind, index)
            return Deduction(
                technique=Technique.UNIT_SUPPORT,
                exclusions=exclusions,
                evidence_cells=candidates,
                explanation=(
                    f"{_unit_name(puzzle, source_ref)}에는 고양이가 정확히 하나 "
                    "필요하고, 표시된 대상 칸은 그 모든 후보와 충돌합니다."
                ),
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
        source_units = _units(puzzle, source_kind)
        active: list[tuple[int, tuple[Cell, ...], frozenset[int]]] = []
        for source_index, source in enumerate(source_units):
            if _has_cat(state, source):
                continue
            candidates = _candidates(state, source)
            if not candidates:
                continue
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
                    explanation=(
                        f"{', '.join(_unit_name(puzzle, ref) for ref in source_refs)}의 "
                        f"후보가 "
                        f"{', '.join(_unit_name(puzzle, ref) for ref in target_refs)}만 "
                        "차지하므로 대상 단위들은 이 고양이들로 예약됩니다."
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
    *UNIT_SUPPORT_FINDERS,
    *CONTAINER_MATCHING_FINDERS,
)


def find_next_deduction(state: LogicSnapshot) -> Deduction | None:
    """쉬운 기법 우선의 안정적인 순서로 첫 추론을 반환한다."""

    for finder in TECHNIQUE_FINDERS:
        deduction = finder(state)
        if deduction is not None:
            return deduction
    return None

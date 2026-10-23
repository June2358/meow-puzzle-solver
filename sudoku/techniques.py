"""불변 솔버 스냅샷 하나에서 수행하는 순수 논리 추론.

모든 finder는 같은 격자와 후보 스냅샷을 받는다. 확정 finder는 해당 스냅샷의
같은 기법으로 증명되는 모든 확정을 묶고, 배치 안의 확정을 탐색에 재사용하지
않는다. 제거 finder는 고정 순서의 첫 패턴을 반환한다. 반환한 변경을 적용하고
상태 스냅샷을 기록하는 책임은 솔버에만 있다."""

from collections.abc import Callable, Iterator
from itertools import combinations
from typing import Final

from .board import Grid
from .solve_types import (
    Assignment,
    CandidateGrid,
    Elimination,
    Technique,
    TechniqueResult,
)
from .topology import (
    BOX_SIZE,
    BOXES,
    CELLS,
    COLS,
    DIGITS,
    PEERS,
    ROWS,
    UNITS,
    Cell,
    Unit,
)

type _TechniqueFinder = Callable[[Grid, CandidateGrid], TechniqueResult | None]
type _NakedSubsetPattern = tuple[tuple[Cell, ...], frozenset[int]]


def _cell_name(cell: Cell) -> str:
    row, col = cell
    return f"R{row + 1}C{col + 1}"


def _unit_name(unit_index: int) -> str:
    if unit_index < len(ROWS):
        return f"행 {unit_index + 1}"
    if unit_index < len(ROWS) + len(COLS):
        return f"열 {unit_index - len(ROWS) + 1}"
    return f"박스 {unit_index - len(ROWS) - len(COLS) + 1}"


def _merge_cells(*groups: tuple[Cell, ...] | Unit) -> tuple[Cell, ...]:
    """중복 없이 처음 나타난 순서로 칸을 반환한다."""

    return tuple(dict.fromkeys(cell for group in groups for cell in group))


def _compatible_assignments(
    assignments: tuple[Assignment, ...],
) -> tuple[Assignment, ...]:
    """모순일 수 있는 상태에서 서로 양립하는 결정적 배치를 유지한다.

    각 확정은 개별적으로 타당하지만 실패한 한 단계 가정에서는 모순 검사 전에
    함께 성립할 수 없는 두 확정이 나타날 수 있다. 하나만 적용해도 모순을
    드러내므로 뒤의 충돌 확정은 제외해 배치 적용 예외를 막는다. 해가 있는
    모든 상태에서는 모든 확정을 변경 없이 반환한다."""

    compatible: list[Assignment] = []
    for assignment in assignments:
        if any(
            assignment.cell == accepted.cell
            or (
                assignment.value == accepted.value
                and assignment.cell in PEERS[accepted.cell]
            )
            for accepted in compatible
        ):
            continue
        compatible.append(assignment)
    return tuple(compatible)


def find_full_house(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """한 스냅샷에서 빈칸이 하나 남은 모든 하우스를 찾는다."""

    assignments_with_units: dict[Assignment, int] = {}
    for unit_index, unit in enumerate(UNITS):
        empty_cells = tuple((row, col) for row, col in unit if grid[row][col] == 0)
        if len(empty_cells) != 1:
            continue

        placed_values = {grid[row][col] for row, col in unit if grid[row][col] != 0}
        missing_values = DIGITS - placed_values
        if len(missing_values) != 1:
            continue

        cell = empty_cells[0]
        value = min(missing_values)
        if value not in candidates[cell[0]][cell[1]]:
            continue
        assignments_with_units.setdefault(Assignment(cell, value), unit_index)

    if not assignments_with_units:
        return None

    assignments = _compatible_assignments(tuple(assignments_with_units))
    if len(assignments) == 1:
        assignment = assignments[0]
        unit_index = assignments_with_units[assignment]
        explanation = (
            f"{_unit_name(unit_index)}에 빈칸이 하나뿐이며 "
            f"빠진 숫자는 {assignment.value}입니다."
        )
    else:
        explanation = (
            f"표시된 {len(assignments)}칸은 각각 해당 단위의 마지막 빈칸입니다."
        )

    context_cells = _merge_cells(
        *(UNITS[assignments_with_units[assignment]] for assignment in assignments)
    )
    return TechniqueResult(
        technique=Technique.FULL_HOUSE,
        assignments=assignments,
        evidence_cells=tuple(
            dict.fromkeys(assignment.cell for assignment in assignments)
        ),
        context_cells=context_cells,
        explanation=explanation,
    )


def find_naked_single(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """변경되지 않은 스냅샷에서 모든 Naked Single을 찾는다."""

    assignments = _compatible_assignments(
        tuple(
            Assignment((row, col), min(candidates[row][col]))
            for row, col in CELLS
            if grid[row][col] == 0 and len(candidates[row][col]) == 1
        )
    )
    if not assignments:
        return None

    if len(assignments) == 1:
        explanation = "표시된 칸에 가능한 후보가 하나뿐입니다."
    else:
        explanation = f"표시된 {len(assignments)}칸은 각각 가능한 후보가 하나뿐입니다."

    return TechniqueResult(
        technique=Technique.NAKED_SINGLE,
        assignments=assignments,
        evidence_cells=tuple(assignment.cell for assignment in assignments),
        explanation=explanation,
    )


def find_hidden_single(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """변경되지 않은 스냅샷에서 모든 Hidden Single을 찾는다."""

    assignments_with_units: dict[Assignment, int] = {}
    for unit_index, unit in enumerate(UNITS):
        for value in sorted(DIGITS):
            positions = tuple(
                (row, col)
                for row, col in unit
                if grid[row][col] == 0 and value in candidates[row][col]
            )
            if len(positions) != 1:
                continue

            cell = positions[0]
            assignments_with_units.setdefault(Assignment(cell, value), unit_index)

    if not assignments_with_units:
        return None

    assignments = _compatible_assignments(tuple(assignments_with_units))
    if len(assignments) == 1:
        assignment = assignments[0]
        unit_index = assignments_with_units[assignment]
        explanation = (
            f"{_unit_name(unit_index)}에서 후보 {assignment.value}이 가능한 "
            "위치가 하나뿐입니다."
        )
    else:
        explanation = (
            f"표시된 {len(assignments)}칸은 각 단위에서 "
            "해당 숫자가 가능한 "
            "유일한 위치입니다."
        )

    context_cells = _merge_cells(
        *(UNITS[assignments_with_units[assignment]] for assignment in assignments)
    )
    return TechniqueResult(
        technique=Technique.HIDDEN_SINGLE,
        assignments=assignments,
        evidence_cells=tuple(
            dict.fromkeys(assignment.cell for assignment in assignments)
        ),
        context_cells=context_cells,
        explanation=explanation,
    )


def find_locked_candidates_pointing(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """첫 Box-to-Line locked-candidate 제거를 찾는다."""

    for box_index, box in enumerate(BOXES):
        box_cells = frozenset(box)
        for value in sorted(DIGITS):
            positions = tuple(
                (row, col)
                for row, col in box
                if grid[row][col] == 0 and value in candidates[row][col]
            )
            if len(positions) < 2:
                continue

            rows = {row for row, _ in positions}
            if len(rows) == 1:
                row = min(rows)
                targets = tuple(
                    cell
                    for cell in ROWS[row]
                    if cell not in box_cells
                    and grid[cell[0]][cell[1]] == 0
                    and value in candidates[cell[0]][cell[1]]
                )
                if targets:
                    eliminations = tuple(
                        Elimination(cell, frozenset({value})) for cell in targets
                    )
                    return TechniqueResult(
                        technique=Technique.LOCKED_CANDIDATES_POINTING,
                        eliminations=eliminations,
                        evidence_cells=positions,
                        context_cells=_merge_cells(box, ROWS[row]),
                        explanation=(
                            f"박스 {box_index + 1}의 후보 {value}가 행 {row + 1}에 "
                            "고정되어 있습니다."
                        ),
                    )

            cols = {col for _, col in positions}
            if len(cols) == 1:
                col = min(cols)
                targets = tuple(
                    cell
                    for cell in COLS[col]
                    if cell not in box_cells
                    and grid[cell[0]][cell[1]] == 0
                    and value in candidates[cell[0]][cell[1]]
                )
                if targets:
                    eliminations = tuple(
                        Elimination(cell, frozenset({value})) for cell in targets
                    )
                    return TechniqueResult(
                        technique=Technique.LOCKED_CANDIDATES_POINTING,
                        eliminations=eliminations,
                        evidence_cells=positions,
                        context_cells=_merge_cells(box, COLS[col]),
                        explanation=(
                            f"박스 {box_index + 1}의 후보 {value}가 열 {col + 1}에 "
                            "고정되어 있습니다."
                        ),
                    )
    return None


def _box_index(cell: Cell) -> int:
    row, col = cell
    return (row // BOX_SIZE) * BOX_SIZE + col // BOX_SIZE


def find_locked_candidates_claiming(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """첫 Line-to-Box locked-candidate 제거를 찾는다."""

    line_groups = (("행", ROWS), ("열", COLS))
    for line_name, lines in line_groups:
        for line_index, line in enumerate(lines):
            line_cells = frozenset(line)
            for value in sorted(DIGITS):
                positions = tuple(
                    (row, col)
                    for row, col in line
                    if grid[row][col] == 0 and value in candidates[row][col]
                )
                if len(positions) < 2:
                    continue

                box_indices = {_box_index(cell) for cell in positions}
                if len(box_indices) != 1:
                    continue

                box_index = min(box_indices)
                box = BOXES[box_index]
                targets = tuple(
                    cell
                    for cell in box
                    if cell not in line_cells
                    and grid[cell[0]][cell[1]] == 0
                    and value in candidates[cell[0]][cell[1]]
                )
                if not targets:
                    continue

                eliminations = tuple(
                    Elimination(cell, frozenset({value})) for cell in targets
                )
                return TechniqueResult(
                    technique=Technique.LOCKED_CANDIDATES_CLAIMING,
                    eliminations=eliminations,
                    evidence_cells=positions,
                    context_cells=_merge_cells(line, box),
                    explanation=(
                        f"{line_name} {line_index + 1}의 후보 {value}가 "
                        f"박스 {box_index + 1}에 고정되어 있습니다."
                    ),
                )
    return None


def _iter_naked_subsets_in_unit(
    grid: Grid,
    candidates: CandidateGrid,
    unit: Unit,
    size: int,
) -> Iterator[_NakedSubsetPattern]:
    """한 단위의 고정된 칸 순서로 Naked Subset 패턴을 생성한다."""

    eligible_cells = tuple(
        (row, col)
        for row, col in unit
        if grid[row][col] == 0 and 2 <= len(candidates[row][col]) <= size
    )
    for evidence_cells in combinations(eligible_cells, size):
        digits = frozenset(
            value for row, col in evidence_cells for value in candidates[row][col]
        )
        if len(digits) == size:
            yield tuple(evidence_cells), digits


def _locked_box_index(evidence_cells: tuple[Cell, ...]) -> int | None:
    """근거가 행/열과 박스의 교차 영역에 있으면 공통 박스를 반환한다."""

    box_indices = {_box_index(cell) for cell in evidence_cells}
    if len(box_indices) != 1:
        return None
    rows = {row for row, _ in evidence_cells}
    cols = {col for _, col in evidence_cells}
    return min(box_indices) if len(rows) == 1 or len(cols) == 1 else None


def _find_locked_naked_subset(
    grid: Grid,
    candidates: CandidateGrid,
    *,
    size: int,
    technique: Technique,
) -> TechniqueResult | None:
    """행/열과 박스의 한 교차 영역에 속한 Naked Subset을 찾는다."""

    line_groups = (("행", ROWS), ("열", COLS))
    for line_name, lines in line_groups:
        for line_index, line in enumerate(lines):
            for evidence_cells, digits in _iter_naked_subsets_in_unit(
                grid,
                candidates,
                line,
                size,
            ):
                box_index = _locked_box_index(evidence_cells)
                if box_index is None:
                    continue

                box = BOXES[box_index]
                evidence_set = frozenset(evidence_cells)
                context_cells = _merge_cells(line, box)
                eliminations = tuple(
                    Elimination(cell, candidates[cell[0]][cell[1]] & digits)
                    for cell in context_cells
                    if cell not in evidence_set
                    and grid[cell[0]][cell[1]] == 0
                    and candidates[cell[0]][cell[1]] & digits
                )
                if not eliminations:
                    continue

                return TechniqueResult(
                    technique=technique,
                    eliminations=eliminations,
                    evidence_cells=evidence_cells,
                    context_cells=context_cells,
                    explanation=(
                        f"{', '.join(_cell_name(cell) for cell in evidence_cells)}가 "
                        f"{line_name} {line_index + 1}과 박스 {box_index + 1}에서 "
                        f"후보 {sorted(digits)}를 독점합니다."
                    ),
                )
    return None


def _find_naked_subset(
    grid: Grid,
    candidates: CandidateGrid,
    *,
    size: int,
    technique: Technique,
) -> TechniqueResult | None:
    """주어진 크기의 첫 일반 Naked Subset 제거를 찾는다."""

    for unit_index, unit in enumerate(UNITS):
        for evidence_cells, digits in _iter_naked_subsets_in_unit(
            grid,
            candidates,
            unit,
            size,
        ):
            if _locked_box_index(evidence_cells) is not None:
                continue

            evidence_set = frozenset(evidence_cells)
            eliminations = tuple(
                Elimination((row, col), candidates[row][col] & digits)
                for row, col in unit
                if (row, col) not in evidence_set
                and grid[row][col] == 0
                and candidates[row][col] & digits
            )
            if not eliminations:
                continue

            return TechniqueResult(
                technique=technique,
                eliminations=eliminations,
                evidence_cells=evidence_cells,
                context_cells=unit,
                explanation=(
                    f"{_unit_name(unit_index)}의 "
                    f"{', '.join(_cell_name(cell) for cell in evidence_cells)}가 "
                    f"후보 {sorted(digits)}를 독점합니다."
                ),
            )
    return None


def _find_hidden_subset(
    grid: Grid,
    candidates: CandidateGrid,
    *,
    size: int,
    technique: Technique,
) -> TechniqueResult | None:
    """주어진 크기의 첫 Hidden Subset 제한을 찾는다."""

    for unit_index, unit in enumerate(UNITS):
        positions_by_digit = {
            value: tuple(
                (row, col)
                for row, col in unit
                if grid[row][col] == 0 and value in candidates[row][col]
            )
            for value in sorted(DIGITS)
        }

        # A digit with more than size positions cannot fit inside this subset.
        eligible_digits = tuple(
            value
            for value in sorted(DIGITS)
            if 0 < len(positions_by_digit[value]) <= size
        )
        for digits_tuple in combinations(eligible_digits, size):
            evidence_cells = tuple(
                sorted(
                    {
                        cell
                        for value in digits_tuple
                        for cell in positions_by_digit[value]
                    }
                )
            )
            if len(evidence_cells) != size:
                continue

            digits = frozenset(digits_tuple)
            eliminations = tuple(
                Elimination((row, col), candidates[row][col] - digits)
                for row, col in evidence_cells
                if candidates[row][col] - digits
            )
            if not eliminations:
                continue

            return TechniqueResult(
                technique=technique,
                eliminations=eliminations,
                evidence_cells=evidence_cells,
                context_cells=unit,
                explanation=(
                    f"{_unit_name(unit_index)}에서 "
                    f"후보 {sorted(digits)}가 표시된 {size}칸에만 존재합니다."
                ),
            )
    return None


def find_locked_pair(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """행/열과 박스에 걸친 첫 Locked Pair 제거를 찾는다."""

    return _find_locked_naked_subset(
        grid,
        candidates,
        size=2,
        technique=Technique.LOCKED_PAIR,
    )


def find_naked_pair(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """첫 Naked Pair 제거를 찾는다."""

    return _find_naked_subset(
        grid,
        candidates,
        size=2,
        technique=Technique.NAKED_PAIR,
    )


def find_locked_triple(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """행/열과 박스에 걸친 첫 Locked Triple 제거를 찾는다."""

    return _find_locked_naked_subset(
        grid,
        candidates,
        size=3,
        technique=Technique.LOCKED_TRIPLE,
    )


def find_naked_triple(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """첫 Naked Triple 제거를 찾는다."""

    return _find_naked_subset(
        grid,
        candidates,
        size=3,
        technique=Technique.NAKED_TRIPLE,
    )


def find_hidden_pair(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """첫 Hidden Pair 제한을 찾는다."""

    return _find_hidden_subset(
        grid,
        candidates,
        size=2,
        technique=Technique.HIDDEN_PAIR,
    )


def find_hidden_triple(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """첫 Hidden Triple 제한을 찾는다."""

    return _find_hidden_subset(
        grid,
        candidates,
        size=3,
        technique=Technique.HIDDEN_TRIPLE,
    )


_TECHNIQUE_FINDERS: Final[tuple[_TechniqueFinder, ...]] = (
    find_full_house,
    find_naked_single,
    find_hidden_single,
    find_locked_pair,
    find_naked_pair,
    find_locked_candidates_pointing,
    find_locked_candidates_claiming,
    find_locked_triple,
    find_naked_triple,
    find_hidden_pair,
    find_hidden_triple,
)


def find_next_deduction(
    grid: Grid,
    candidates: CandidateGrid,
) -> TechniqueResult | None:
    """쉬운 기법부터 고정 순서로 첫 가능한 추론을 반환한다."""

    if not any(0 in row for row in grid):
        return None
    for finder in _TECHNIQUE_FINDERS:
        result = finder(grid, candidates)
        if result is not None:
            return result
    return None

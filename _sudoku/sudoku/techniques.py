"""Pure logical deductions over one immutable solver snapshot.

Every finder receives the same grid and candidate snapshot. Placement finders
batch every assignment justified by the same technique in that snapshot;
assignments found in the batch are never fed back into the search.
Elimination finders return the first pattern in a deterministic order. The
solver is solely responsible for applying a returned delta and recording a
state snapshot.
"""

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
    """Return cells in first-seen order without duplicates."""

    return tuple(dict.fromkeys(cell for group in groups for cell in group))


def _compatible_assignments(
    assignments: tuple[Assignment, ...],
) -> tuple[Assignment, ...]:
    """Keep a deterministic compatible batch from a possibly contradictory state.

    Every assignment is sound on its own. A failed one-ply branch can,
    however, expose two forced placements that cannot coexist before the
    solver's next contradiction check. Applying one of those placements is
    enough to expose the contradiction, so the later conflicting placement is
    left out instead of making batch application raise an exception. On every
    satisfiable state this returns all assignments unchanged.
    """

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
    """Find every house whose final empty cell is visible in one snapshot."""

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
    """Find every Naked Single visible in one unchanged state snapshot."""

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
    """Find every Hidden Single visible in one unchanged state snapshot."""

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
    """Find the first Box-to-Line locked-candidate elimination."""

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
    """Find the first Line-to-Box locked-candidate elimination."""

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
    """Yield Naked Subset patterns in one unit's stable cell order."""

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
    """Return the shared box when evidence is confined to a line-box crossing."""

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
    """Find a Naked Subset confined to one line-box intersection."""

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
    """Find the first ordinary Naked Subset elimination of one size."""

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
    """Find the first Hidden Subset restriction of one size."""

    for unit_index, unit in enumerate(UNITS):
        positions_by_digit = {
            value: tuple(
                (row, col)
                for row, col in unit
                if grid[row][col] == 0 and value in candidates[row][col]
            )
            for value in sorted(DIGITS)
        }

        for digits_tuple in combinations(sorted(DIGITS), size):
            if any(not positions_by_digit[value] for value in digits_tuple):
                continue

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
    """Find the first Locked Pair elimination across its line and box."""

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
    """Find the first Naked Pair elimination."""

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
    """Find the first Locked Triple elimination across its line and box."""

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
    """Find the first Naked Triple elimination."""

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
    """Find the first Hidden Pair restriction."""

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
    """Find the first Hidden Triple restriction."""

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
    """Return the first available deduction in stable easiest-first order."""

    for finder in _TECHNIQUE_FINDERS:
        result = finder(grid, candidates)
        if result is not None:
            return result
    return None

import pytest

from sudoku.techniques import (
    find_locked_candidates_claiming,
    find_locked_candidates_pointing,
)
from sudoku.topology import SIZE


@pytest.mark.parametrize("transpose", [False, True])
@pytest.mark.parametrize("claiming", [False, True])
def test_locked_candidates_preserve_axis_evidence_and_targets(
    claiming: bool, transpose: bool
) -> None:
    evidence = ((0, 0), (0, 1))
    targets = ((1, 2),) if claiming else ((0, 3), (0, 4))
    if transpose:
        evidence = tuple((col, row) for row, col in evidence)
        targets = tuple((col, row) for row, col in targets)
    possible = frozenset((*evidence, *targets))
    grid = tuple((0,) * SIZE for _ in range(SIZE))
    candidates = tuple(
        tuple(
            frozenset({1}) if (row, col) in possible else frozenset()
            for col in range(SIZE)
        )
        for row in range(SIZE)
    )
    finder = (
        find_locked_candidates_claiming if claiming else find_locked_candidates_pointing
    )

    result = finder(grid, candidates)

    assert result is not None
    assert result.evidence_cells == evidence
    assert tuple(item.cell for item in result.eliminations) == targets
    assert all(item.values == frozenset({1}) for item in result.eliminations)


@pytest.mark.parametrize(
    "finder", [find_locked_candidates_pointing, find_locked_candidates_claiming]
)
def test_sudoku_lock_needs_two_unplaced_candidates(finder) -> None:
    grid = tuple((0,) * SIZE for _ in range(SIZE))
    candidates = tuple(
        tuple(
            frozenset({1}) if (row, col) in {(0, 0), (0, 3), (3, 0)} else frozenset()
            for col in range(SIZE)
        )
        for row in range(SIZE)
    )
    assert finder(grid, candidates) is None

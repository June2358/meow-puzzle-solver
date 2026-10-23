import pytest

from meow.model import Puzzle
from meow.solve_types import Technique, UnitKind, UnitRef
from meow.state import CellState, LogicSnapshot
from meow.techniques import find_region_line_lock


@pytest.mark.parametrize(
    ("possible", "technique", "source", "target", "evidence", "exclusions"),
    [
        (
            ((0, 0), (0, 1), (0, 2)),
            Technique.REGION_TO_ROW_LOCK,
            UnitKind.REGION,
            UnitKind.ROW,
            ((0, 0), (0, 1)),
            ((0, 2),),
        ),
        (
            ((0, 0), (1, 0), (2, 0)),
            Technique.REGION_TO_COLUMN_LOCK,
            UnitKind.REGION,
            UnitKind.COLUMN,
            ((0, 0), (1, 0)),
            ((2, 0),),
        ),
        (
            ((0, 0), (1, 0), (1, 1)),
            Technique.ROW_TO_REGION_LOCK,
            UnitKind.ROW,
            UnitKind.REGION,
            ((0, 0),),
            ((1, 0), (1, 1)),
        ),
        (
            ((0, 0), (0, 1), (1, 1), (0, 2), (1, 3)),
            Technique.COLUMN_TO_REGION_LOCK,
            UnitKind.COLUMN,
            UnitKind.REGION,
            ((0, 0),),
            ((0, 1), (1, 1)),
        ),
    ],
)
def test_region_line_lock_preserves_priority_and_supports_single_candidates(
    possible, technique, source, target, evidence, exclusions
) -> None:
    puzzle = Puzzle(tuple(tuple(row) for row in ("AABB", "AABB", "CCDD", "CCDD")))
    state = LogicSnapshot(
        puzzle,
        tuple(
            tuple(
                CellState.POSSIBLE if (row, col) in possible else CellState.EXCLUDED
                for col in range(4)
            )
            for row in range(4)
        ),
    )

    result = find_region_line_lock(state)

    assert result is not None
    assert result.technique is technique
    assert result.evidence_units == (UnitRef(source, 0), UnitRef(target, 0))
    assert result.evidence_cells == evidence
    assert result.exclusions == exclusions


def test_region_line_lock_skips_sources_with_placed_cats() -> None:
    puzzle = Puzzle((("A", "A"), ("B", "B")))
    state = LogicSnapshot(
        puzzle,
        ((CellState.CAT, CellState.POSSIBLE), (CellState.CAT, CellState.POSSIBLE)),
    )

    assert find_region_line_lock(state) is None

from meow.model import Puzzle
from meow.puzzle_catalog import load_preset
from meow.solve_types import (
    SOLVER_ALGORITHM_LABELS,
    TECHNIQUE_ALGORITHMS,
    TECHNIQUE_LABELS,
    SolverAlgorithm,
    Technique,
    UnitKind,
)
from meow.state import LogicState
from meow.techniques import (
    CONTAINER_MATCHING_FINDERS,
    UNIT_SUPPORT_FINDERS,
    _active_units,
    find_next_deduction,
)


def test_every_algorithm_and_technique_has_display_metadata() -> None:
    assert set(SOLVER_ALGORITHM_LABELS) == set(SolverAlgorithm)
    assert set(TECHNIQUE_LABELS) == set(Technique)
    assert set(TECHNIQUE_ALGORITHMS) == set(Technique)


def test_deduction_techniques_are_grouped_by_algorithm() -> None:
    assert (
        TECHNIQUE_ALGORITHMS[Technique.PLACED_CAT_ELIMINATION]
        is SolverAlgorithm.DIRECT_PROPAGATION
    )
    assert TECHNIQUE_ALGORITHMS[Technique.UNIT_SUPPORT] is SolverAlgorithm.UNIT_SUPPORT
    assert (
        TECHNIQUE_ALGORITHMS[Technique.HALL_LOCK] is SolverAlgorithm.CONTAINER_MATCHING
    )
    assert (
        TECHNIQUE_ALGORITHMS[Technique.PROBE_ELIMINATION]
        is SolverAlgorithm.SINGLETON_PROBING
    )


def test_deductions_prefer_direct_propagation_then_container_matching() -> None:
    snapshot = LogicState(load_preset("보통")).snapshot()

    assert any(finder(snapshot) is not None for finder in UNIT_SUPPORT_FINDERS)
    assert any(finder(snapshot) is not None for finder in CONTAINER_MATCHING_FINDERS)
    deduction = find_next_deduction(snapshot)

    assert deduction is not None
    assert deduction.algorithm is SolverAlgorithm.CONTAINER_MATCHING

    state = LogicState(snapshot.puzzle)
    state.place_cat((0, 0))
    deduction = find_next_deduction(state.snapshot())
    assert deduction is not None
    assert deduction.algorithm is SolverAlgorithm.DIRECT_PROPAGATION


def test_active_units_skip_cats_and_empty_units_without_reordering() -> None:
    puzzle = Puzzle.from_region_grid((tuple("ABCD"),) * 4)
    state = LogicState(puzzle)
    state.place_cat((2, 2))
    for cell in (*puzzle.rows[1], (0, 3)):
        state.exclude(cell)

    assert tuple(_active_units(state.snapshot(), UnitKind.ROW)) == (
        (0, puzzle.rows[0], ((0, 0), (0, 1), (0, 2))),
        (3, puzzle.rows[3], ((3, 0), (3, 1), (3, 2), (3, 3))),
    )

from meow.puzzle_catalog import load_preset
from meow.solve_types import (
    SOLVER_ALGORITHM_LABELS,
    TECHNIQUE_ALGORITHMS,
    TECHNIQUE_LABELS,
    SolverAlgorithm,
    Technique,
)
from meow.state import LogicState
from meow.techniques import (
    CONTAINER_MATCHING_FINDERS,
    UNIT_SUPPORT_FINDERS,
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

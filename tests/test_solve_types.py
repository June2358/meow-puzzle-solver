from meow.solve_types import (
    SOLVER_ALGORITHM_LABELS,
    TECHNIQUE_ALGORITHMS,
    TECHNIQUE_LABELS,
    SolverAlgorithm,
    Technique,
)
from meow.techniques import (
    CONTAINER_MATCHING_FINDERS,
    DIRECT_PROPAGATION_FINDERS,
    TECHNIQUE_FINDERS,
    UNIT_SUPPORT_FINDERS,
)


def test_every_algorithm_and_technique_has_display_metadata() -> None:
    assert set(SOLVER_ALGORITHM_LABELS) == set(SolverAlgorithm)
    assert SOLVER_ALGORITHM_LABELS == {
        SolverAlgorithm.DIRECT_PROPAGATION: "Basic Deductions",
        SolverAlgorithm.UNIT_SUPPORT: "Crowding",
        SolverAlgorithm.CONTAINER_MATCHING: "Container Locks",
        SolverAlgorithm.SINGLETON_PROBING: "One-Step Lookahead",
        SolverAlgorithm.BACKTRACK_SEARCH: "Backtracking",
    }
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


def test_deterministic_finders_follow_algorithm_order() -> None:
    assert (
        *DIRECT_PROPAGATION_FINDERS,
        *UNIT_SUPPORT_FINDERS,
        *CONTAINER_MATCHING_FINDERS,
    ) == TECHNIQUE_FINDERS

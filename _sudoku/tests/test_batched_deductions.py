from sample_puzzles import grid_from_string

from sudoku.board import Grid, Puzzle
from sudoku.solve_types import CandidateGrid, Technique
from sudoku.solver_state import SolverState
from sudoku.techniques import (
    find_hidden_single,
    find_hidden_triple,
    find_naked_single,
    find_naked_triple,
)
from sudoku.topology import CELLS, DIGITS, SIZE, Cell

CASCADE_GRID = (
    "534678912672195348198342567859701403426803791713904806961537284287419635345286179"
)
HIDDEN_ONLY_GRID = (
    "030000000002000000000000000850000000400050091000020000900000000000009000000200000"
)


def state_from_string(grid: str) -> SolverState:
    return SolverState(Puzzle(grid_from_string(grid)))


def state_snapshot(state: SolverState) -> tuple[Grid, CandidateGrid]:
    return state.to_grid(), state.candidate_grid()


def synthetic_snapshot(
    overrides: dict[Cell, frozenset[int]],
) -> tuple[Grid, CandidateGrid]:
    grid = tuple((0,) * SIZE for _ in range(SIZE))
    candidates = tuple(
        tuple(overrides.get((row, col), DIGITS) for col in range(SIZE))
        for row in range(SIZE)
    )
    return grid, candidates


def test_naked_single_batches_only_placements_visible_in_the_same_snapshot() -> None:
    state = state_from_string(CASCADE_GRID)

    first = find_naked_single(*state_snapshot(state))

    assert first is not None
    assert first.technique is Technique.NAKED_SINGLE
    assert len(first.assignments) == 2

    for assignment in first.assignments:
        assert state.set_value(assignment.cell, assignment.value)

    second = find_naked_single(*state_snapshot(state))

    assert second is not None
    assert len(second.assignments) == 3


def test_hidden_single_batches_all_visible_placements() -> None:
    state = state_from_string(HIDDEN_ONLY_GRID)

    assert find_naked_single(*state_snapshot(state)) is None
    result = find_hidden_single(*state_snapshot(state))

    assert result is not None
    assert result.technique is Technique.HIDDEN_SINGLE
    assert len(result.assignments) == 2


def test_naked_triple_eliminates_its_digits_from_the_rest_of_the_unit() -> None:
    snapshot = synthetic_snapshot(
        {
            (0, 0): frozenset({1, 2}),
            (0, 3): frozenset({1, 3}),
            (0, 6): frozenset({2, 3}),
        }
    )

    result = find_naked_triple(*snapshot)

    assert result is not None
    assert result.technique is Technique.NAKED_TRIPLE
    assert result.evidence_cells == ((0, 0), (0, 3), (0, 6))
    assert any(
        elimination.cell == (0, 1) and elimination.values == frozenset({1, 2, 3})
        for elimination in result.eliminations
    )


def test_hidden_triple_removes_other_candidates_from_its_cells() -> None:
    non_triple_digits = DIGITS - {1, 2, 3}
    overrides = {
        cell: non_triple_digits for cell in CELLS if cell[0] == 0 and cell[1] >= 3
    }
    overrides.update(
        {
            (0, 0): frozenset({1, 2, 4}),
            (0, 1): frozenset({1, 3, 5}),
            (0, 2): frozenset({2, 3, 6}),
        }
    )

    result = find_hidden_triple(*synthetic_snapshot(overrides))

    assert result is not None
    assert result.technique is Technique.HIDDEN_TRIPLE
    assert result.evidence_cells == ((0, 0), (0, 1), (0, 2))
    assert {item.cell: item.values for item in result.eliminations} == {
        (0, 0): frozenset({4}),
        (0, 1): frozenset({5}),
        (0, 2): frozenset({6}),
    }

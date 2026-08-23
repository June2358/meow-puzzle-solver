from __future__ import annotations

from itertools import combinations

from meow.exact_solver import ExactStatus
from meow.model import Puzzle
from meow.puzzle_catalog import load_preset
from meow.solve_types import LogicStatus, Technique
from meow.solver import SolveOutcome, solve


def _puzzle(*rows: str) -> Puzzle:
    return Puzzle.from_region_grid(tuple(tuple(row) for row in rows))


REFUTATION_UNIQUE = load_preset("전문가")

MULTIPLE = _puzzle(
    "AAACB",
    "AACCB",
    "DDCBB",
    "EECCB",
    "EECCB",
)

BACKTRACKING_UNIQUE = load_preset("극한")

BACKTRACKING_UNSOLVABLE = _puzzle(
    "ABCDDDDD",
    "AACDDEDE",
    "AACFEEDE",
    "AACFFEEE",
    "GACCFFEH",
    "GAACGGEH",
    "GGGGGGEC",
    "GGGGGHHH",
)


def _is_valid_solution(
    puzzle: Puzzle,
    solution: tuple[tuple[int, int], ...] | None,
) -> bool:
    if solution is None:
        return False
    cells = set(solution)
    return (
        len(cells) == puzzle.size
        and {row for row, _ in cells} == set(range(puzzle.size))
        and {column for _, column in cells} == set(range(puzzle.size))
        and {puzzle.region_of(cell) for cell in cells} == set(range(puzzle.size))
        and all(
            not puzzle.conflict(first, second)
            for first, second in combinations(cells, 2)
        )
    )


def test_refutation_solves_after_basic_logic_stalls() -> None:
    result = solve(REFUTATION_UNIQUE)

    assert result.initial_logic_result.status is LogicStatus.STALLED
    assert result.exact_result.status is ExactStatus.UNIQUE
    assert result.outcome is SolveOutcome.SOLVED_WITH_REFUTATION
    assert result.refutation_rounds
    assert not result.used_backtracking
    assert _is_valid_solution(REFUTATION_UNIQUE, result.solution)


def test_stalled_refutation_switches_to_backtracking() -> None:
    result = solve(BACKTRACKING_UNIQUE)

    assert result.exact_result.status is ExactStatus.UNIQUE
    assert result.outcome is SolveOutcome.SOLVED_WITH_BACKTRACKING
    assert result.used_backtracking
    assert result.refutation_rounds[-1].stalled
    assert _is_valid_solution(BACKTRACKING_UNIQUE, result.solution)


def test_multiple_puzzle_returns_one_valid_solution() -> None:
    result = solve(MULTIPLE)

    assert result.exact_result.status is ExactStatus.MULTIPLE
    assert result.solution is not None
    assert _is_valid_solution(MULTIPLE, result.solution)


def test_unsolvable_puzzle_returns_no_solution() -> None:
    result = solve(BACKTRACKING_UNSOLVABLE)

    assert result.exact_result.status is ExactStatus.UNSOLVABLE
    assert result.outcome is SolveOutcome.UNSOLVABLE
    assert result.used_backtracking
    assert result.solution is None


def test_refutation_is_not_nested_and_a_contradiction_becomes_x() -> None:
    result = solve(REFUTATION_UNIQUE)

    assert all(
        step.deduction.technique is not Technique.REFUTATION_ELIMINATION
        for round_ in result.refutation_rounds
        for assumption in round_.assumptions
        for step in assumption.logic_result.steps
    )

    eliminated_rounds = [
        round_ for round_ in result.refutation_rounds if round_.elimination is not None
    ]
    assert eliminated_rounds
    for round_ in eliminated_rounds:
        contradiction = next(
            assumption
            for assumption in round_.assumptions
            if assumption.status is LogicStatus.CONTRADICTION
        )
        elimination = round_.elimination
        assert elimination is not None
        refutation_step = next(
            step
            for step in elimination.steps
            if step.deduction.technique is Technique.REFUTATION_ELIMINATION
        )
        assert refutation_step.deduction.exclusions == (contradiction.assumption,)
        assert refutation_step.after.is_excluded(contradiction.assumption)

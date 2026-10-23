from __future__ import annotations

from itertools import combinations

from meow.exact_solver import ExactStatus
from meow.logic_solver import solve_logically
from meow.model import Puzzle
from meow.puzzle_catalog import load_preset
from meow.solve_types import LogicStatus, Technique
from meow.solver import SolveOutcome, _rank_probe_candidates, solve
from meow.state import LogicState


def _puzzle(*rows: str) -> Puzzle:
    return Puzzle.from_region_grid(tuple(tuple(row) for row in rows))


PROBING_UNIQUE = load_preset("전문가")

MULTIPLE = _puzzle(
    "AAACB",
    "AACCB",
    "DDCBB",
    "EECCB",
    "EECCB",
)

BACKTRACK_SEARCH_MULTIPLE = _puzzle(
    "ABCDE",
    "ABCDE",
    "ABCDE",
    "ABCDE",
    "ABCDE",
)

BACKTRACK_SEARCH_UNSOLVABLE = _puzzle(
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


def test_probing_solves_after_deterministic_logic_stalls() -> None:
    result = solve(PROBING_UNIQUE)

    assert result.initial_logic_result.status is LogicStatus.STALLED
    assert result.exact_result.status is ExactStatus.UNIQUE
    assert result.outcome is SolveOutcome.SOLVED_WITH_PROBING
    assert result.probing_rounds
    assert not result.used_backtrack_search
    assert _is_valid_solution(PROBING_UNIQUE, result.solution)


def test_no_ranked_probe_candidate_switches_to_backtrack_search() -> None:
    result = solve(BACKTRACK_SEARCH_MULTIPLE)

    assert result.initial_logic_result.status is LogicStatus.STALLED
    assert result.exact_result.status is ExactStatus.MULTIPLE
    assert result.outcome is SolveOutcome.SOLVED_WITH_BACKTRACK_SEARCH
    assert result.used_backtrack_search
    assert result.probing_rounds[-1].candidates == ()
    assert result.probing_rounds[-1].probes == ()
    assert result.probing_rounds[-1].stalled
    assert _is_valid_solution(BACKTRACK_SEARCH_MULTIPLE, result.solution)


def test_stalled_ranked_probes_switch_to_backtrack_search(
    stalled_probe_puzzle: Puzzle,
) -> None:
    result = solve(stalled_probe_puzzle)
    round_ = result.probing_rounds[-1]

    assert result.exact_result.status is ExactStatus.MULTIPLE
    assert result.outcome is SolveOutcome.SOLVED_WITH_BACKTRACK_SEARCH
    assert round_.candidates
    assert round_.probes
    assert all(probe.status is LogicStatus.STALLED for probe in round_.probes)
    assert round_.stalled
    assert _is_valid_solution(stalled_probe_puzzle, result.solution)


def test_multiple_puzzle_returns_one_valid_solution() -> None:
    result = solve(MULTIPLE)

    assert result.exact_result.status is ExactStatus.MULTIPLE
    assert _is_valid_solution(MULTIPLE, result.solution)
    assert result.outcome is SolveOutcome.SOLVED_WITH_PROBING
    assert not result.used_backtrack_search
    round_ = result.probing_rounds[-1]
    assert round_.elimination is None
    assert round_.probes[-1].status is LogicStatus.SOLVED_LOGICALLY
    assert result.solution == tuple(
        sorted(round_.probes[-1].logic_result.final_state.cats)
    )


def test_unsolvable_puzzle_returns_no_solution() -> None:
    result = solve(BACKTRACK_SEARCH_UNSOLVABLE)

    assert result.exact_result.status is ExactStatus.UNSOLVABLE
    assert result.outcome is SolveOutcome.UNSOLVABLE
    assert result.solution is None
    assert not result.used_backtrack_search
    elimination = result.probing_rounds[-1].elimination
    assert elimination is not None
    assert elimination.status is LogicStatus.CONTRADICTION


def test_probe_score_counts_unique_new_cats_and_new_pair_units() -> None:
    snapshot = solve_logically(PROBING_UNIQUE).final_state
    score = next(
        item for item in _rank_probe_candidates(snapshot) if item.cell == (0, 2)
    )

    # 여섯 단위가 singleton이 되지만 같은 칸을 중복 제거하면 CAT은 넷이다.
    assert score.forced_cats == ((1, 4), (2, 0), (3, 1), (4, 3))
    assert score.forced_cat_count == 4
    assert score.new_pair_units == 2
    assert score.cell not in score.forced_cats


def test_probe_candidates_use_s1_then_s2_then_coordinate_order() -> None:
    snapshot = solve_logically(load_preset("극한")).final_state
    ranked = _rank_probe_candidates(snapshot)
    s2_only_candidate = (1, 3)

    assert len(snapshot.possible_cells) == 36
    assert len(ranked) == 19
    assert all(item.forced_cat_count > 0 for item in ranked)
    assert [
        (item.cell, item.forced_cat_count, item.new_pair_units) for item in ranked[:6]
    ] == [
        ((2, 5), 4, 1),
        ((2, 4), 3, 2),
        ((2, 3), 3, 1),
        ((5, 6), 2, 5),
        ((2, 7), 2, 3),
        ((6, 6), 2, 3),
    ]
    assert s2_only_candidate in snapshot.possible_cells
    assert s2_only_candidate not in {item.cell for item in ranked}


def test_probe_score_ignores_units_already_satisfied_by_a_cat() -> None:
    state = LogicState(BACKTRACK_SEARCH_MULTIPLE)
    state.place_cat((4, 4))
    state.exclude((4, 2))
    state.exclude((4, 3))

    ranked_cells = {item.cell for item in _rank_probe_candidates(state.snapshot())}

    # R5에는 이미 CAT이 있다. R1C1이 남은 R5 후보를 하나로 줄이더라도
    # 그것은 새 CAT이 아니므로 probing 실행 조건으로 세지 않는다.
    assert (0, 0) not in ranked_cells


def test_refuted_probe_restarts_with_fresh_candidate_scores() -> None:
    result = solve(PROBING_UNIQUE)

    assert tuple(round_.probes[0].assumption for round_ in result.probing_rounds) == (
        (0, 2),
        (1, 4),
        (0, 3),
        (3, 1),
    )
    assert all(round_.elimination is not None for round_ in result.probing_rounds)
    for previous, current in zip(
        result.probing_rounds[:-1],
        result.probing_rounds[1:],
        strict=True,
    ):
        assert current.before.is_excluded(previous.probes[0].assumption)


def test_probing_is_not_nested_and_a_contradiction_becomes_x() -> None:
    result = solve(PROBING_UNIQUE)

    assert all(
        step.deduction.technique is not Technique.PROBE_ELIMINATION
        for round_ in result.probing_rounds
        for probe in round_.probes
        for step in probe.logic_result.steps
    )

    eliminated_rounds = [
        round_ for round_ in result.probing_rounds if round_.elimination is not None
    ]
    assert eliminated_rounds
    for round_ in eliminated_rounds:
        contradiction = next(
            probe
            for probe in round_.probes
            if probe.status is LogicStatus.CONTRADICTION
        )
        elimination = round_.elimination
        assert elimination is not None
        probing_step = next(
            step
            for step in elimination.steps
            if step.deduction.technique is Technique.PROBE_ELIMINATION
        )
        assert probing_step.deduction.exclusions == (contradiction.assumption,)
        assert probing_step.after.is_excluded(contradiction.assumption)

from __future__ import annotations

from meow.model import Puzzle
from meow.puzzle_catalog import load_preset
from meow.solve_types import LogicStatus, Technique
from meow.solver import AssumptionResult, SolveResult, solve
from meow.timeline import PlaybackFrame, TimelineKind, build_timeline


def _puzzle(*rows: str) -> Puzzle:
    return Puzzle.from_region_grid(tuple(tuple(row) for row in rows))


REFUTATION = load_preset("전문가")

SOLVED_ASSUMPTION = _puzzle(
    "AAACB",
    "AACCB",
    "DDCBB",
    "EECCB",
    "EECCB",
)

BACKTRACKING = load_preset("극한")


def _assert_initial_logic_is_shown(
    result: SolveResult,
    timeline: tuple[PlaybackFrame, ...],
) -> None:
    logic_end = next(
        index
        for index, frame in enumerate(timeline)
        if frame.kind is TimelineKind.LOGIC_END
    )
    shown_steps = [
        frame.logic_step
        for frame in timeline[1:logic_end]
        if frame.kind is TimelineKind.LOGIC_STEP
    ]
    assert shown_steps == list(result.initial_logic_result.steps)


def _assert_assumption_is_shown(
    assumption: AssumptionResult,
    timeline: tuple[PlaybackFrame, ...],
) -> int:
    start = next(
        index
        for index, frame in enumerate(timeline)
        if frame.kind is TimelineKind.ASSUME
        and frame.active_assumption == assumption.assumption
    )
    end = next(
        index
        for index in range(start + 1, len(timeline))
        if timeline[index].kind is TimelineKind.ASSUMPTION_END
    )
    shown_steps = [
        frame.logic_step
        for frame in timeline[start + 1 : end]
        if frame.kind is TimelineKind.LOGIC_STEP
    ]

    assert shown_steps == list(assumption.logic_result.steps)
    assert all(
        frame.active_assumption == assumption.assumption
        for frame in timeline[start : end + 1]
    )
    return end


def test_contradiction_timeline_shows_restore_x_and_final_result() -> None:
    result = solve(REFUTATION)
    timeline = build_timeline(result)
    contradiction = next(
        assumption
        for assumption in result.refutation_rounds[0].assumptions
        if assumption.status is LogicStatus.CONTRADICTION
    )

    assert timeline[0].kind is TimelineKind.START
    _assert_initial_logic_is_shown(result, timeline)
    assert TimelineKind.REFUTATION_SELECT in {frame.kind for frame in timeline}
    assumption_end = _assert_assumption_is_shown(contradiction, timeline)
    assert timeline[assumption_end + 1].kind is TimelineKind.RESTORE

    x_frame = next(
        frame
        for frame in timeline[assumption_end + 2 :]
        if frame.logic_step is not None
        and frame.logic_step.deduction.technique is Technique.REFUTATION_ELIMINATION
    )
    assert x_frame.active_assumption is None
    assert x_frame.logic_step is not None
    assert x_frame.logic_step.deduction.exclusions == (contradiction.assumption,)
    assert timeline[-1].kind is TimelineKind.FINAL


def test_solved_assumption_runs_directly_to_the_final_result() -> None:
    result = solve(SOLVED_ASSUMPTION)
    timeline = build_timeline(result)
    round_ = result.refutation_rounds[-1]
    solved = next(
        assumption
        for assumption in round_.assumptions
        if assumption.status is LogicStatus.SOLVED_LOGICALLY
    )

    _assert_initial_logic_is_shown(result, timeline)
    assumption_ends = [
        _assert_assumption_is_shown(assumption, timeline)
        for assumption in round_.assumptions
    ]
    solved_end = assumption_ends[round_.assumptions.index(solved)]
    assert timeline[solved_end + 1].kind is TimelineKind.FINAL
    assert TimelineKind.BACKTRACKING not in {frame.kind for frame in timeline}


def test_stalled_assumptions_are_restored_before_backtracking() -> None:
    result = solve(BACKTRACKING)
    timeline = build_timeline(result)
    round_ = result.refutation_rounds[-1]

    assert round_.stalled
    _assert_initial_logic_is_shown(result, timeline)
    for assumption in round_.assumptions:
        assumption_end = _assert_assumption_is_shown(assumption, timeline)
        assert timeline[assumption_end + 1].kind is TimelineKind.RESTORE
    assert [frame.kind for frame in timeline[-2:]] == [
        TimelineKind.BACKTRACKING,
        TimelineKind.FINAL,
    ]
    assert timeline[-1].snapshot.cats == frozenset(result.solution or ())

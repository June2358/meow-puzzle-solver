from __future__ import annotations

from meow.model import Puzzle
from meow.puzzle_catalog import load_preset
from meow.solve_types import LogicStatus, Technique, UnitKind
from meow.solver import ProbeResult, SolveResult, solve
from meow.timeline import PlaybackFrame, TimelineKind, build_timeline


def _puzzle(*rows: str) -> Puzzle:
    return Puzzle.from_region_grid(tuple(tuple(row) for row in rows))


PROBING = load_preset("전문가")

SOLVED_PROBE = _puzzle(
    "AAACB",
    "AACCB",
    "DDCBB",
    "EECCB",
    "EECCB",
)

BACKTRACK_SEARCH = load_preset("극한")


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


def _assert_probe_is_shown(
    probe: ProbeResult,
    timeline: tuple[PlaybackFrame, ...],
) -> int:
    start = next(
        index
        for index, frame in enumerate(timeline)
        if frame.kind is TimelineKind.PROBE_START
        and frame.active_assumption == probe.assumption
    )
    end = next(
        index
        for index in range(start + 1, len(timeline))
        if timeline[index].kind is TimelineKind.PROBE_END
    )
    shown_steps = [
        frame.logic_step
        for frame in timeline[start + 1 : end]
        if frame.kind is TimelineKind.LOGIC_STEP
    ]

    assert shown_steps == list(probe.logic_result.steps)
    assert all(
        frame.active_assumption == probe.assumption
        for frame in timeline[start : end + 1]
    )
    return end


def test_contradiction_timeline_shows_restore_x_and_final_result() -> None:
    result = solve(PROBING)
    timeline = build_timeline(result)
    contradiction = next(
        probe
        for probe in result.probing_rounds[0].probes
        if probe.status is LogicStatus.CONTRADICTION
    )

    assert timeline[0].kind is TimelineKind.START
    _assert_initial_logic_is_shown(result, timeline)
    assert TimelineKind.PROBING_SELECT in {frame.kind for frame in timeline}
    assumption_end = _assert_probe_is_shown(contradiction, timeline)
    assert timeline[assumption_end + 1].kind is TimelineKind.RESTORE

    x_frame = next(
        frame
        for frame in timeline[assumption_end + 2 :]
        if frame.logic_step is not None
        and frame.logic_step.deduction.technique is Technique.PROBE_ELIMINATION
    )
    assert x_frame.active_assumption is None
    assert x_frame.logic_step is not None
    assert x_frame.logic_step.deduction.exclusions == (contradiction.assumption,)
    assert timeline[-1].kind is TimelineKind.FINAL


def test_solved_probe_runs_directly_to_the_final_result() -> None:
    result = solve(SOLVED_PROBE)
    timeline = build_timeline(result)
    round_ = result.probing_rounds[-1]
    solved = next(
        probe for probe in round_.probes if probe.status is LogicStatus.SOLVED_LOGICALLY
    )

    _assert_initial_logic_is_shown(result, timeline)
    probe_ends = [_assert_probe_is_shown(probe, timeline) for probe in round_.probes]
    solved_end = probe_ends[round_.probes.index(solved)]
    assert timeline[solved_end + 1].kind is TimelineKind.FINAL
    assert TimelineKind.BACKTRACK_SEARCH not in {frame.kind for frame in timeline}


def test_stalled_probes_are_restored_before_backtrack_search() -> None:
    result = solve(BACKTRACK_SEARCH)
    timeline = build_timeline(result)
    round_ = result.probing_rounds[-1]

    assert round_.stalled
    _assert_initial_logic_is_shown(result, timeline)
    for probe in round_.probes:
        assumption_end = _assert_probe_is_shown(probe, timeline)
        assert timeline[assumption_end + 1].kind is TimelineKind.RESTORE
    assert [frame.kind for frame in timeline[-2:]] == [
        TimelineKind.BACKTRACK_SEARCH,
        TimelineKind.FINAL,
    ]
    assert timeline[-1].snapshot.cats == frozenset(result.solution or ())


def test_region_labels_are_replaced_by_color_references() -> None:
    source = load_preset("쉬움")
    renamed = {
        label: f"SECRET_REGION_{index}"
        for index, label in enumerate(source.region_labels)
    }
    puzzle = Puzzle.from_region_grid(
        tuple(tuple(renamed[label] for label in row) for row in source.region_grid)
    )
    timeline = build_timeline(solve(puzzle))
    visible_text = "\n".join(
        text
        for frame in timeline
        for text in (frame.title, frame.message)
    )

    assert "SECRET_REGION_" not in visible_text
    region_frames = [frame for frame in timeline if frame.region_indices]
    assert region_frames
    for frame in region_frames:
        assert len(frame.region_indices) == len(set(frame.region_indices))
        if frame.logic_step is None:
            continue
        expected = tuple(
            dict.fromkeys(
                ref.index
                for ref in frame.logic_step.deduction.evidence_units
                if ref.kind is UnitKind.REGION
            )
        )
        assert frame.region_indices == expected

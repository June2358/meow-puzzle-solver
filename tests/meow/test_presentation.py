from meow.model import Puzzle
from meow.presentation import describe_frame
from meow.puzzle_catalog import load_preset
from meow.solve_types import SOLVER_ALGORITHM_LABELS, Technique, UnitKind
from meow.solver import solve
from puzzle_common.board import region_palette
from puzzle_common.engine import LogicStatus
from puzzle_common.presentation import FrameKind, build_frames


def test_contradictory_probe_restores_then_refutes_and_resumes_logic():
    result = solve(load_preset("전문가"))
    frames = build_frames(result)
    first_probe = result.run.probing_rounds[0].probes[0]
    end = next(
        index for index, frame in enumerate(frames) if frame.kind is FrameKind.PROBE_END
    )

    assert first_probe.logic_result.status is LogicStatus.CONTRADICTION
    assert frames[0].kind is FrameKind.START
    assert [frame.kind for frame in frames[end : end + 3]] == [
        FrameKind.PROBE_END,
        FrameKind.RESTORE,
        FrameKind.REFUTATION,
    ]
    refutation = frames[end + 2]
    assert refutation.deduction.technique is Technique.PROBE_ELIMINATION
    assert refutation.deduction.exclusions == (first_probe.assumption,)
    assert refutation.active_assumption is None
    assert refutation.snapshot.is_excluded(first_probe.assumption)
    assert sum(frame.kind is FrameKind.LOGIC_END for frame in frames) == (
        1 + len(result.run.probing_rounds)
    )
    assert frames[-1].kind is FrameKind.FINAL


def test_solved_probe_goes_directly_to_final_without_restore():
    puzzle = Puzzle.from_region_grid(
        tuple(tuple(row) for row in ("AAACB", "AACCB", "DDCBB", "EECCB", "EECCB"))
    )
    result = solve(puzzle)
    frames = build_frames(result)

    assert frames[-2].kind is FrameKind.PROBE_END
    assert frames[-2].status is LogicStatus.SOLVED
    assert frames[-1].kind is FrameKind.FINAL
    assert FrameKind.SEARCH not in {frame.kind for frame in frames}
    assert frames[-1].snapshot is result.solution


def test_shared_frames_keep_native_deductions_and_probe_context():
    result = solve(load_preset("전문가"))
    frames = build_frames(result)
    logic_end = next(
        index for index, frame in enumerate(frames) if frame.kind is FrameKind.LOGIC_END
    )

    assert [frame.deduction for frame in frames[1:logic_end]] == [
        step.deduction for step in result.run.initial_logic_result.steps
    ]
    for frame in frames:
        if frame.deduction is not None:
            details = describe_frame(frame, result)
            assert details.title == SOLVER_ALGORITHM_LABELS[frame.deduction.algorithm]
            assert bool(details.assumption) == (frame.active_assumption is not None)
            assert bool(details.annotations) == (frame.active_assumption is not None)


def test_stalled_probes_restore_before_search(stalled_probe_puzzle):
    result = solve(stalled_probe_puzzle)
    frames = build_frames(result)
    restores = [frame for frame in frames if frame.kind is FrameKind.RESTORE]

    assert len(restores) == len(result.run.probing_rounds[-1].probes)
    assert all(frame.active_assumption is None for frame in restores)
    assert all(
        "다음 우선순위 후보" in describe_frame(frame, result).reason
        for frame in restores[:-1]
    )
    assert "분기 탐색" in describe_frame(restores[-1], result).reason
    assert [frame.kind for frame in frames[-2:]] == [FrameKind.SEARCH, FrameKind.FINAL]
    assert frames[-1].snapshot is result.solution


def test_no_probe_candidate_is_explained_before_search():
    puzzle = Puzzle.from_region_grid((tuple("ABCDE"),) * 5)
    result = solve(puzzle)
    frames = build_frames(result)
    selection = next(
        frame for frame in frames if frame.kind is FrameKind.PROBING_SELECT
    )
    details = describe_frame(selection, result)

    assert details.title.endswith("대상 없음")
    assert "새 고양이를 확정하는 후보가 없습니다" in details.reason
    assert frames[-2].kind is FrameKind.SEARCH


def test_region_names_stay_private_and_region_colors_follow_evidence():
    source = load_preset("쉬움")
    renamed = {
        label: f"SECRET_REGION_{index}"
        for index, label in enumerate(source.region_labels)
    }
    puzzle = Puzzle.from_region_grid(
        tuple(tuple(renamed[label] for label in row) for row in source.region_grid)
    )
    result = solve(puzzle)
    frames = build_frames(result)
    palette = region_palette(puzzle.region_labels)
    region_frames = []

    for frame in frames:
        details = describe_frame(frame, result)
        assert "SECRET_REGION_" not in details.title + details.reason
        if details.region_colors:
            region_frames.append(frame)
        if frame.deduction is not None:
            indices = tuple(
                dict.fromkeys(
                    ref.index
                    for ref in frame.deduction.evidence_units
                    if ref.kind is UnitKind.REGION
                )
            )
            assert details.region_colors == tuple(
                palette[puzzle.region_labels[index]] for index in indices
            )
    assert region_frames

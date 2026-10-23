"""One native result and playback traversal shared by every puzzle."""

from dataclasses import FrozenInstanceError

import pytest

from puzzle_common.engine import (
    LogicRun,
    LogicStatus,
    LogicStep,
    Outcome,
    ProbeRound,
    ProbeRun,
    SolveResult,
    SolveRun,
)
from puzzle_common.presentation import FrameKind, build_frames


def logic(status, start, end=None, steps=(), witness=None):
    return LogicRun(status, start, start if end is None else end, steps, witness)


def test_refutation_restores_root_then_resumes_native_deductions():
    delta, refutation, resumed, witness = object(), object(), object(), object()
    initial = logic(
        LogicStatus.STALLED, "initial", "root", (LogicStep("initial", "root", delta),)
    )
    failed = logic(LogicStatus.CONTRADICTION, "assumed", "bad", witness=witness)
    elimination = logic(
        LogicStatus.SOLVED,
        "root",
        "solved",
        (
            LogicStep("root", "refuted", refutation),
            LogicStep("refuted", "solved", resumed),
        ),
    )
    round_ = ProbeRound(
        "root", ("choice", "untried"), (ProbeRun("choice", failed),), elimination
    )
    result = SolveResult(
        Outcome.UNIQUE, SolveRun(initial, (round_,), ("solved",), False)
    )
    frames = build_frames(result)

    assert [frame.kind for frame in frames] == [
        FrameKind.START,
        FrameKind.DEDUCTION,
        FrameKind.LOGIC_END,
        FrameKind.PROBING_SELECT,
        FrameKind.PROBE_START,
        FrameKind.PROBE_END,
        FrameKind.RESTORE,
        FrameKind.REFUTATION,
        FrameKind.DEDUCTION,
        FrameKind.LOGIC_END,
        FrameKind.FINAL,
    ]
    assert frames[1].deduction is delta
    assert frames[7].deduction is refutation
    assert frames[8].deduction is resumed
    assert frames[5].contradiction is witness
    assert frames[5].status is frames[6].status is LogicStatus.CONTRADICTION
    assert frames[6].snapshot == "root"
    assert frames[7].assumption == frames[6].assumption == "choice"
    assert frames[7].active_assumption is frames[6].active_assumption is None
    assert frames[4].active_assumption == frames[5].active_assumption == "choice"
    assert all(frame.candidates is round_.candidates for frame in frames[3:7])
    assert all(frame.probe_index == 1 for frame in frames[4:7])
    assert all(frame.contradiction is None for i, frame in enumerate(frames) if i != 5)
    assert result.run.initial_logic_result is initial
    assert result.root_state == result.solution == frames[-1].snapshot == "solved"


def test_successful_probe_retains_native_solution_without_restore_or_search():
    solution, alternative, delta = object(), object(), object()
    initial = logic(LogicStatus.STALLED, "root")
    branch = logic(
        LogicStatus.SOLVED,
        "assumed",
        solution,
        (LogicStep("assumed", solution, delta),),
    )
    round_ = ProbeRound("root", ("choice",), (ProbeRun("choice", branch),))
    result = SolveResult(
        Outcome.MULTIPLE, SolveRun(initial, (round_,), (solution, alternative), False)
    )
    frames = build_frames(result)

    assert [frame.kind for frame in frames] == [
        FrameKind.START,
        FrameKind.LOGIC_END,
        FrameKind.PROBING_SELECT,
        FrameKind.PROBE_START,
        FrameKind.DEDUCTION,
        FrameKind.PROBE_END,
        FrameKind.FINAL,
    ]
    assert frames[4].deduction is delta
    assert frames[4].active_assumption == "choice"
    assert frames[5].status is LogicStatus.SOLVED
    assert result.solution is frames[-1].snapshot is solution
    assert result.root_state == "root"


@pytest.mark.parametrize("decisions", [(), ("first", "second")])
def test_failed_search_finishes_on_root_not_last_stalled_branch(decisions):
    initial = logic(LogicStatus.STALLED, "root")
    probes = tuple(ProbeRun(d, logic(LogicStatus.STALLED, d)) for d in decisions)
    run = SolveRun(initial, (ProbeRound("root", decisions, probes),), (), True)
    result = SolveResult(Outcome.UNSOLVABLE, run)
    frames = build_frames(result)

    assert [frame.kind for frame in frames[-2:]] == [FrameKind.SEARCH, FrameKind.FINAL]
    assert result.solution is None
    assert result.root_state == frames[-2].snapshot == frames[-1].snapshot == "root"
    assert frames[-2].candidates is decisions
    restores = [frame for frame in frames if frame.kind is FrameKind.RESTORE]
    assert [frame.probe_index for frame in restores] == list(
        range(1, len(decisions) + 1)
    )
    assert all(frame.status is LogicStatus.STALLED for frame in restores)


def test_contradictory_refutation_exposes_root_witness_before_final():
    initial = logic(LogicStatus.STALLED, "root")
    failed = logic(LogicStatus.CONTRADICTION, "branch", witness="branch witness")
    elimination = logic(
        LogicStatus.CONTRADICTION,
        "root",
        "bad root",
        (LogicStep("root", "bad root", "remove choice"),),
        "root witness",
    )
    round_ = ProbeRound("root", ("choice",), (ProbeRun("choice", failed),), elimination)
    frames = build_frames(
        SolveResult(Outcome.UNSOLVABLE, SolveRun(initial, (round_,), (), False))
    )

    assert frames[-2].kind is FrameKind.LOGIC_END
    assert frames[-2].status is LogicStatus.CONTRADICTION
    assert frames[-2].contradiction == "root witness"
    assert frames[-2].active_assumption is None
    assert frames[-1].snapshot == "bad root"


@pytest.mark.parametrize(
    "outcome, status, solutions",
    [
        (Outcome.UNIQUE, LogicStatus.SOLVED, ("final",)),
        (Outcome.MULTIPLE, LogicStatus.SOLVED, ("final",)),
        (Outcome.UNSOLVABLE, LogicStatus.CONTRADICTION, ()),
    ],
)
def test_terminal_result_is_immutable_and_allows_one_multiple_representative(
    outcome, status, solutions
):
    result = SolveResult(
        outcome, SolveRun(logic(status, "initial", "final"), (), solutions, False)
    )
    frames = build_frames(result)

    assert [frame.kind for frame in frames] == [
        FrameKind.START,
        FrameKind.LOGIC_END,
        FrameKind.FINAL,
    ]
    assert frames[-1].snapshot == "final"
    with pytest.raises(FrozenInstanceError):
        result.outcome = Outcome.MULTIPLE
    with pytest.raises(FrozenInstanceError):
        frames[0].snapshot = "changed"


@pytest.mark.parametrize(
    "outcome, solutions",
    [
        (Outcome.UNSOLVABLE, ("solution",)),
        (Outcome.UNIQUE, ()),
        (Outcome.MULTIPLE, ()),
    ],
)
def test_result_rejects_outcome_solution_disagreement(outcome, solutions):
    run = SolveRun(logic(LogicStatus.STALLED, "root"), (), solutions, False)
    with pytest.raises(ValueError):
        SolveResult(outcome, run)


def test_result_rejects_untyped_outcome_or_run():
    run = SolveRun(logic(LogicStatus.SOLVED, "solution"), (), ("solution",), False)
    with pytest.raises(TypeError):
        SolveResult("unique", run)
    with pytest.raises(TypeError):
        SolveResult(Outcome.UNIQUE, object())

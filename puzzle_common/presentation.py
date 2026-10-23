"""One playback traversal over native engine records for every puzzle."""

from dataclasses import dataclass
from enum import StrEnum

from .engine import LogicRun, LogicStatus, SolveResult


class FrameKind(StrEnum):
    START = "start"
    DEDUCTION = "deduction"
    LOGIC_END = "logic_end"
    PROBING_SELECT = "probing_select"
    PROBE_START = "probe_start"
    PROBE_END = "probe_end"
    RESTORE = "restore"
    REFUTATION = "refutation"
    SEARCH = "search"
    FINAL = "final"


@dataclass(frozen=True, slots=True)
class PlaybackFrame[Snapshot, Deduction, Decision, Witness]:
    """Native state and event context; puzzle views supply words and drawings."""

    kind: FrameKind
    snapshot: Snapshot
    deduction: Deduction | None = None
    assumption: Decision | None = None
    status: LogicStatus | None = None
    contradiction: Witness | None = None
    candidates: tuple[Decision, ...] = ()
    probe_index: int = 0

    @property
    def active_assumption(self) -> Decision | None:
        return (
            None
            if self.kind in (FrameKind.RESTORE, FrameKind.REFUTATION)
            else self.assumption
        )


def _deduction_frames[Snapshot, Deduction, Decision, Witness](
    logic: LogicRun[Snapshot, Deduction, Witness],
    assumption: Decision | None = None,
    *,
    refuted_assumption: Decision | None = None,
) -> list[PlaybackFrame[Snapshot, Deduction, Decision, Witness]]:
    return [
        PlaybackFrame(
            kind=FrameKind.REFUTATION
            if index == 0 and refuted_assumption is not None
            else FrameKind.DEDUCTION,
            snapshot=step.after,
            deduction=step.deduction,
            assumption=refuted_assumption
            if index == 0 and refuted_assumption is not None
            else assumption,
        )
        for index, step in enumerate(logic.steps)
    ]


def _logic_end[Snapshot, Deduction, Decision, Witness](
    logic: LogicRun[Snapshot, Deduction, Witness],
) -> PlaybackFrame[Snapshot, Deduction, Decision, Witness]:
    return PlaybackFrame(
        FrameKind.LOGIC_END,
        logic.final_state,
        status=logic.status,
        contradiction=logic.contradiction,
    )


def build_frames[Snapshot, Deduction, Decision, Witness](
    result: SolveResult[Snapshot, Deduction, Decision, Witness],
) -> tuple[PlaybackFrame[Snapshot, Deduction, Decision, Witness], ...]:
    """Show deduction, probing, restoration and finalization in one fixed order."""
    run = result.run
    initial = run.initial_logic_result
    frames = [PlaybackFrame(FrameKind.START, initial.initial_state)]
    frames.extend(_deduction_frames(initial))
    frames.append(_logic_end(initial))

    for round_ in run.probing_rounds:
        frames.append(
            PlaybackFrame(
                FrameKind.PROBING_SELECT, round_.before, candidates=round_.candidates
            )
        )
        for index, probe in enumerate(round_.probes, 1):
            logic = probe.logic_result
            frames.append(
                PlaybackFrame(
                    FrameKind.PROBE_START,
                    logic.initial_state,
                    assumption=probe.assumption,
                    candidates=round_.candidates,
                    probe_index=index,
                )
            )
            frames.extend(_deduction_frames(logic, probe.assumption))
            frames.append(
                PlaybackFrame(
                    FrameKind.PROBE_END,
                    logic.final_state,
                    assumption=probe.assumption,
                    status=logic.status,
                    contradiction=logic.contradiction,
                    candidates=round_.candidates,
                    probe_index=index,
                )
            )
            if logic.status is not LogicStatus.SOLVED:
                frames.append(
                    PlaybackFrame(
                        FrameKind.RESTORE,
                        round_.before,
                        assumption=probe.assumption,
                        status=logic.status,
                        candidates=round_.candidates,
                        probe_index=index,
                    )
                )
        if round_.elimination is not None:
            frames.extend(
                _deduction_frames(
                    round_.elimination,
                    refuted_assumption=round_.probes[-1].assumption,
                )
            )
            frames.append(_logic_end(round_.elimination))

    if run.used_backtrack_search:
        frames.append(
            PlaybackFrame(
                FrameKind.SEARCH,
                result.root_state,
                candidates=run.probing_rounds[-1].candidates,
            )
        )
    frames.append(
        PlaybackFrame(
            FrameKind.FINAL,
            result.solution if result.solution is not None else result.root_state,
        )
    )
    return tuple(frames)

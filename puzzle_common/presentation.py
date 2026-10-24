"""One playback traversal over native engine records for every puzzle."""

from dataclasses import dataclass
from enum import StrEnum

from .coordinates import cell_name
from .engine import LogicRun, LogicStatus, SolveResult
from .ui_style import ACCENT, ORANGE
from .view import FrameData, Grid, PlaybackDetails


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


def describe_frame(
    definition, grid: Grid, frame: PlaybackFrame, result: SolveResult, data: FrameData
) -> PlaybackDetails:
    """Present native algorithm facts through one set of playback messages."""
    decision = ""
    if data.decision is not None:
        cell, value = data.decision
        decision = (
            f"{cell_name(cell)} = {definition.value_label if value is None else value}"
        )
    if frame.deduction is not None:
        title = "귀류 결론" if frame.kind is FrameKind.REFUTATION else "논리 기법"
        reason = data.reason or data.technique
    elif frame.kind is FrameKind.START:
        title, reason = "초기 상태", "입력한 문제에서 논리 풀이를 시작합니다."
    elif frame.kind is FrameKind.PROBING_SELECT:
        title = "가정 후보 선택"
        reason = (
            f"{definition.probe_description} 대상 {len(frame.candidates)}개를 순서대로 살펴봅니다."
            if frame.candidates
            else "실행할 가정 후보가 없어 탐색으로 넘어갑니다."
        )
    elif frame.kind is FrameKind.PROBE_START:
        title, reason = (
            "한 단계 가정",
            f"{decision}로 두고 추가 가정 없이 기존 논리를 적용합니다.",
        )
    elif frame.kind is FrameKind.RESTORE:
        title, reason = (
            "원래 상태 복원",
            f"{decision} 가정을 마치고 원래 상태로 돌아갑니다.",
        )
    elif frame.kind in (FrameKind.LOGIC_END, FrameKind.PROBE_END):
        if frame.status is LogicStatus.CONTRADICTION:
            title, reason = "모순", data.contradiction
        elif frame.status is LogicStatus.SOLVED:
            title, reason = "논리 완료", "추가 가정 없이 해 하나를 완성했습니다."
        else:
            title, reason = "논리 정체", "현재 논리 기법으로 더 진행할 수 없습니다."
    elif frame.kind is FrameKind.SEARCH:
        title, reason = (
            "백트래킹 전환",
            "한 단계 가정으로 결론을 내지 못해 현재 상태에서 탐색합니다.",
        )
    elif result.outcome.value == "unsolvable":
        title, reason = "해 없음", "현재 입력으로 가능한 해가 없습니다."
    else:
        title = "풀이 완료"
        reason = (
            "해가 둘 이상 존재합니다. 표시한 보드는 가능한 해 중 하나입니다."
            if result.outcome.value == "multiple"
            else "유일한 해를 확인했습니다."
        )
    effects = []
    if data.placements:
        items = tuple(
            dict.fromkeys(
                f"{cell_name(cell)} = {definition.value_label if value is None else value}"
                for cell, value in data.placements
            )
        )
        label = (
            f"{definition.value_label} 확정" if definition.value_label else "확정 칸"
        )
        effects.append((f"{label} · {len(items)}", items))
    if data.eliminations:
        items = tuple(
            dict.fromkeys(
                f"{cell_name(cell)}: {', '.join(map(str, values))}"
                if values
                else f"{cell_name(cell)} = X"
                for cell, values in data.eliminations
            )
        )
        label = (
            "후보 제거" if any(values for _, values in data.eliminations) else "X 기입"
        )
        effects.append((f"{label} · {len(items)}", items))
    annotations = [(data.technique, ACCENT)] if data.technique else []
    if frame.active_assumption is not None:
        annotations.append(("한 단계 가정 중", ORANGE))
    region_colors = ()
    if data.region_labels:
        from .board import region_palette

        palette = region_palette(
            tuple(
                dict.fromkeys(
                    value for row in grid for value in row if value is not None
                )
            )
        )
        region_colors = tuple(palette[label] for label in data.region_labels)
    return PlaybackDetails(
        title=title,
        reason=reason or title,
        effects=tuple(effects),
        annotations=tuple(annotations),
        assumption=decision if frame.active_assumption is not None else "",
        region_colors=region_colors,
    )

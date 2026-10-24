"""MEOW wording, effects, and region colors for a common playback frame."""

from puzzle_common.board import region_palette
from puzzle_common.coordinates import cell_name as _cell_name
from puzzle_common.engine import LogicStatus, Outcome, SolveResult
from puzzle_common.presentation import FrameKind, PlaybackFrame
from puzzle_common.ui_style import ORANGE
from puzzle_common.view import PlaybackDetails

from .model import Cell
from .solve_types import (
    SOLVER_ALGORITHM_LABELS,
    TECHNIQUE_LABELS,
    SolverAlgorithm,
    UnitKind,
)

_LOGIC_END_TITLES = {
    LogicStatus.SOLVED: "결정적 추론 완료",
    LogicStatus.STALLED: "결정적 추론 정체",
    LogicStatus.CONTRADICTION: "결정적 추론 모순",
}
_PROBE_END_TITLES = {
    LogicStatus.SOLVED: "가정 결과 해결",
    LogicStatus.STALLED: "가정 결과 정체",
    LogicStatus.CONTRADICTION: "가정 결과 모순",
}
_PROBING_LABEL = SOLVER_ALGORITHM_LABELS[SolverAlgorithm.SINGLETON_PROBING]
_SEARCH_LABEL = SOLVER_ALGORITHM_LABELS[SolverAlgorithm.BACKTRACK_SEARCH]


def _logic_message(status: LogicStatus, contradiction: str | None) -> str:
    if status is LogicStatus.SOLVED:
        return "결정적 추론만으로 해결했습니다."
    if status is LogicStatus.STALLED:
        return "현재 구현된 논리 기법으로 더 진행할 수 없습니다."
    return contradiction or ""


def _ranked_candidates_text(cells: tuple[Cell, ...], limit: int = 6) -> str:
    shown = ", ".join(_cell_name(cell) for cell in cells[:limit])
    remaining = len(cells) - limit
    return shown if remaining <= 0 else f"{shown} 외 {remaining}칸"


def _title_and_reason(frame: PlaybackFrame, result: SolveResult) -> tuple[str, str]:
    if frame.deduction is not None:
        deduction = frame.deduction
        return (
            SOLVER_ALGORITHM_LABELS[deduction.algorithm],
            deduction.explanation
            or f"{TECHNIQUE_LABELS[deduction.technique]}을 적용했습니다.",
        )
    if frame.kind is FrameKind.START:
        return "풀이 시작", "빈 보드에서 결정적 추론을 시작합니다."
    if frame.kind is FrameKind.LOGIC_END:
        return _LOGIC_END_TITLES[frame.status], _logic_message(
            frame.status, frame.contradiction
        )
    if frame.kind is FrameKind.PROBING_SELECT:
        if frame.candidates:
            return (
                f"{_PROBING_LABEL} · 후보 선택",
                "고양이로 가정했을 때 다른 미완성 단위에서 새 고양이가 "
                "즉시 확정되는 후보만 선택했습니다. 새 고양이 수, 새 2후보 "
                "단위 수, 좌표 순으로 가정합니다. "
                f"대상 {len(frame.candidates)}칸: "
                f"{_ranked_candidates_text(frame.candidates)}",
            )
        return (
            f"{_PROBING_LABEL} · 대상 없음",
            "가정 직후 새 고양이를 확정하는 후보가 없습니다. "
            "한 단계 가정을 생략하고 분기 탐색으로 넘어갑니다.",
        )
    if frame.kind is FrameKind.PROBE_START:
        cell = _cell_name(frame.assumption)
        return (
            f"{_PROBING_LABEL} · 후보 {frame.probe_index}/{len(frame.candidates)}",
            f"{cell}에 고양이를 가정하고 결정적 추론을 끝까지 적용합니다.",
        )
    if frame.kind is FrameKind.PROBE_END:
        cell = _cell_name(frame.assumption)
        if frame.status is LogicStatus.CONTRADICTION:
            detail = frame.contradiction or "가능한 배치 조건이 깨졌습니다."
            reason = f"{cell}에 고양이를 놓으면 모순입니다. {detail}"
        elif frame.status is LogicStatus.SOLVED:
            reason = f"{cell}을 가정한 뒤 결정적 추론만으로 완성했습니다."
        else:
            reason = f"{cell} 가정에서 결정적 추론이 더 진행되지 않습니다."
        return _PROBE_END_TITLES[frame.status], reason
    if frame.kind is FrameKind.RESTORE:
        cell = _cell_name(frame.assumption)
        if frame.status is LogicStatus.CONTRADICTION:
            next_action = f"모순이므로 {cell}을 X로 확정합니다."
        elif frame.probe_index == len(frame.candidates):
            next_action = "모든 실행 대상이 정체하여 분기 탐색으로 넘어갑니다."
        else:
            next_action = "결론이 없어 다음 우선순위 후보로 넘어갑니다."
        return (
            f"가정 종료 · {cell}",
            f"임시 가정을 제거하고 원본 상태로 돌아갑니다. {next_action}",
        )
    if frame.kind is FrameKind.SEARCH:
        if frame.candidates:
            reason = (
                "새 고양이를 즉시 확정하는 후보들을 한 번씩 가정해도 "
                "결론이 없었습니다. 임시 가정이 없는 현재 상태에서 "
                f"{_SEARCH_LABEL}으로 답 하나를 찾습니다."
            )
        else:
            reason = (
                "한 단계 가정의 실행 조건을 만족하는 후보가 없습니다. "
                f"현재 상태에서 {_SEARCH_LABEL}으로 답 하나를 찾습니다."
            )
        return _SEARCH_LABEL, reason

    run = result.run
    if result.outcome is Outcome.MULTIPLE:
        method = _SEARCH_LABEL if run.used_backtrack_search else _PROBING_LABEL
        return (
            "최종 결과 · 복수해",
            f"{method}으로 찾은 첫 해를 표시합니다. 다른 해도 존재합니다.",
        )
    if result.outcome is Outcome.UNSOLVABLE:
        if run.used_backtrack_search:
            reason = (
                f"{_PROBING_LABEL}에서 결론을 내지 못해 {_SEARCH_LABEL}했지만 "
                "유효한 해가 없습니다."
            )
        else:
            terminal = run.initial_logic_result
            if run.probing_rounds and run.probing_rounds[-1].elimination is not None:
                terminal = run.probing_rounds[-1].elimination
            reason = _logic_message(terminal.status, terminal.contradiction)
        return "최종 결과 · 해 없음", reason
    if run.used_backtrack_search:
        reason = (
            f"{_PROBING_LABEL}이 막힌 상태에서 {_SEARCH_LABEL}으로 해를 찾았습니다."
        )
    elif run.probing_rounds:
        reason = f"{_PROBING_LABEL} 과정에서 해를 찾았습니다."
    else:
        reason = "결정적 추론만으로 해결했습니다."
    return "최종 결과 · 유일해", reason


def _effect_groups(frame: PlaybackFrame, result: SolveResult):
    if frame.deduction is not None:
        groups = []
        for label, value, cells in (
            ("고양이 확정", "고양이", frame.deduction.placements),
            ("X 기입", "X", frame.deduction.exclusions),
        ):
            if cells:
                groups.append(
                    (
                        f"{label} · {len(cells)}",
                        tuple(f"{_cell_name(cell)} = {value}" for cell in cells),
                    )
                )
        return tuple(groups)
    if frame.kind is FrameKind.RESTORE:
        return (
            ("가정 제거 · 1", (f"{_cell_name(frame.assumption)} 원래 상태로 복원",)),
        )
    if frame.kind is FrameKind.SEARCH:
        return (("전환", (f"{_SEARCH_LABEL}으로 답 하나 찾기",)),)
    if frame.kind is FrameKind.FINAL:
        if result.outcome is Outcome.UNSOLVABLE:
            return (("최종 판정", ("가능한 고양이 배치 없음",)),)
        qualifier = "대표 해" if result.outcome is Outcome.MULTIPLE else "유일해"
        return (
            ("최종 배치", (f"고양이 {len(frame.snapshot.cats)}마리 · {qualifier}",)),
        )
    return ()


def describe_frame(frame: PlaybackFrame, result: SolveResult) -> PlaybackDetails:
    """Describe one native frame without rebuilding or traversing the trace."""

    title, reason = _title_and_reason(frame, result)
    snapshot = frame.snapshot
    puzzle = snapshot.puzzle
    if frame.deduction is not None:
        region_indices = tuple(
            dict.fromkeys(
                ref.index
                for ref in frame.deduction.evidence_units
                if ref.kind is UnitKind.REGION
            )
        )
    elif frame.kind in (FrameKind.LOGIC_END, FrameKind.PROBE_END) and (
        frame.status is LogicStatus.CONTRADICTION
    ):
        region_indices = tuple(
            index
            for index, region in enumerate(puzzle.regions)
            if not snapshot.cats_in(region) and not snapshot.candidates_for(region)
        )
    else:
        region_indices = ()
    palette = region_palette(puzzle.region_labels)
    return PlaybackDetails(
        title=title,
        reason=reason or title,
        effects=_effect_groups(frame, result),
        annotations=((_PROBING_LABEL, ORANGE),)
        if frame.kind is FrameKind.DEDUCTION and frame.active_assumption is not None
        else (),
        assumption=f"{_cell_name(frame.active_assumption)} = 고양이"
        if frame.active_assumption is not None
        else "",
        region_colors=tuple(
            palette[puzzle.region_labels[index]] for index in region_indices
        ),
    )

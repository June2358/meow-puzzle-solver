"""결정적 추론과 한 단계 가정 기록을 화면 재생용 프레임으로 변환한다."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from puzzle_common.coordinates import cell_name as _cell_name

from .exact_solver import ExactStatus
from .model import Cell
from .solve_types import (
    SOLVER_ALGORITHM_LABELS,
    TECHNIQUE_LABELS,
    LogicResult,
    LogicStatus,
    LogicStep,
    SolverAlgorithm,
    UnitKind,
    UnitRef,
)
from .solver import ProbeResult, ProbingRound, SolveOutcome, SolveResult
from .state import CellState, LogicSnapshot


class TimelineKind(StrEnum):
    """재생 화면에서 구분하는 프레임 종류."""

    START = "start"
    LOGIC_STEP = "logic_step"
    LOGIC_END = "logic_end"
    PROBING_SELECT = "probing_select"
    PROBE_START = "probe_start"
    PROBE_END = "probe_end"
    RESTORE = "restore"
    BACKTRACK_SEARCH = "backtrack_search"
    FINAL = "final"


@dataclass(frozen=True, slots=True)
class PlaybackFrame:
    """화면에 바로 그릴 수 있는 하나의 불변 프레임."""

    kind: TimelineKind
    snapshot: LogicSnapshot
    title: str
    message: str
    active_assumption: Cell | None = None
    focus_cells: tuple[Cell, ...] = ()
    region_indices: tuple[int, ...] = ()
    logic_step: LogicStep | None = None


_LOGIC_END_TITLES = {
    LogicStatus.SOLVED_LOGICALLY: "결정적 추론 완료",
    LogicStatus.STALLED: "결정적 추론 정체",
    LogicStatus.CONTRADICTION: "결정적 추론 모순",
}

_PROBE_END_TITLES = {
    LogicStatus.SOLVED_LOGICALLY: "가정 결과 해결",
    LogicStatus.STALLED: "가정 결과 정체",
    LogicStatus.CONTRADICTION: "가정 결과 모순",
}

_PROBING_LABEL = SOLVER_ALGORITHM_LABELS[SolverAlgorithm.SINGLETON_PROBING]
_SEARCH_LABEL = SOLVER_ALGORITHM_LABELS[SolverAlgorithm.BACKTRACK_SEARCH]


def _cells_text(cells: tuple[Cell, ...]) -> str:
    return ", ".join(_cell_name(cell) for cell in cells)


def _ranked_candidates_text(cells: tuple[Cell, ...], limit: int = 6) -> str:
    shown = _cells_text(cells[:limit])
    remaining = len(cells) - limit
    return shown if remaining <= 0 else f"{shown} 외 {remaining}칸"


def _step_focus(step: LogicStep) -> tuple[Cell, ...]:
    deduction = step.deduction
    return tuple(
        dict.fromkeys(
            (
                *deduction.evidence_cells,
                *deduction.placements,
                *deduction.exclusions,
            )
        )
    )


def _region_indices(refs: tuple[UnitRef, ...]) -> tuple[int, ...]:
    return tuple(
        dict.fromkeys(ref.index for ref in refs if ref.kind is UnitKind.REGION)
    )


def _empty_region_indices(snapshot: LogicSnapshot) -> tuple[int, ...]:
    return tuple(
        index
        for index, region in enumerate(snapshot.puzzle.regions)
        if not snapshot.cats_in(region) and not snapshot.candidates_for(region)
    )


def _append_logic_steps(
    frames: list[PlaybackFrame],
    result: LogicResult,
    *,
    active_assumption: Cell | None = None,
) -> None:
    for step in result.steps:
        label = TECHNIQUE_LABELS[step.deduction.technique]
        title = SOLVER_ALGORITHM_LABELS[step.deduction.algorithm]
        frames.append(
            PlaybackFrame(
                kind=TimelineKind.LOGIC_STEP,
                snapshot=step.after,
                title=title,
                message=step.deduction.explanation or f"{label}을 적용했습니다.",
                active_assumption=active_assumption,
                focus_cells=_step_focus(step),
                region_indices=_region_indices(step.deduction.evidence_units),
                logic_step=step,
            )
        )


def _probe_message(result: ProbeResult) -> str:
    cell = _cell_name(result.assumption)
    if result.status is LogicStatus.CONTRADICTION:
        detail = result.logic_result.message or "가능한 배치 조건이 깨졌습니다."
        return f"{cell}에 고양이를 놓으면 모순입니다. {detail}"
    if result.status is LogicStatus.SOLVED_LOGICALLY:
        return f"{cell}을 가정한 뒤 결정적 추론만으로 완성했습니다."
    return f"{cell} 가정에서 결정적 추론이 더 진행되지 않습니다."


def _append_probing_round(
    frames: list[PlaybackFrame],
    round_: ProbingRound,
) -> None:
    if round_.candidates:
        selection_title = f"{_PROBING_LABEL} · 후보 선택"
        selection_message = (
            "고양이로 가정했을 때 다른 미완성 단위에서 새 고양이가 "
            "즉시 확정되는 후보만 선택했습니다. 새 고양이 수, 새 2후보 "
            "단위 수, 좌표 순으로 가정합니다. "
            f"대상 {len(round_.candidates)}칸: "
            f"{_ranked_candidates_text(round_.candidates)}"
        )
    else:
        selection_title = f"{_PROBING_LABEL} · 대상 없음"
        selection_message = (
            "가정 직후 새 고양이를 확정하는 후보가 없습니다. "
            "한 단계 가정을 생략하고 분기 탐색으로 넘어갑니다."
        )
    frames.append(
        PlaybackFrame(
            kind=TimelineKind.PROBING_SELECT,
            snapshot=round_.before,
            title=selection_title,
            message=selection_message,
            focus_cells=round_.candidates,
        )
    )

    for index, result in enumerate(round_.probes, start=1):
        cell = _cell_name(result.assumption)
        frames.append(
            PlaybackFrame(
                kind=TimelineKind.PROBE_START,
                snapshot=result.logic_result.initial_state,
                title=f"{_PROBING_LABEL} · 후보 {index}/{len(round_.candidates)}",
                message=(
                    f"{cell}에 고양이를 가정하고 결정적 추론을 끝까지 적용합니다."
                ),
                active_assumption=result.assumption,
                focus_cells=(result.assumption,),
            )
        )
        _append_logic_steps(
            frames,
            result.logic_result,
            active_assumption=result.assumption,
        )
        frames.append(
            PlaybackFrame(
                kind=TimelineKind.PROBE_END,
                snapshot=result.logic_result.final_state,
                title=_PROBE_END_TITLES[result.status],
                message=_probe_message(result),
                active_assumption=result.assumption,
                focus_cells=(result.assumption,),
                region_indices=(
                    _empty_region_indices(result.logic_result.final_state)
                    if result.status is LogicStatus.CONTRADICTION
                    else ()
                ),
            )
        )
        if result.status is not LogicStatus.SOLVED_LOGICALLY:
            if result.status is LogicStatus.CONTRADICTION:
                next_action = f"모순이므로 {cell}을 X로 확정합니다."
            elif index == len(round_.probes) and round_.stalled:
                next_action = "모든 실행 대상이 정체하여 분기 탐색으로 넘어갑니다."
            else:
                next_action = "결론이 없어 다음 우선순위 후보로 넘어갑니다."
            frames.append(
                PlaybackFrame(
                    kind=TimelineKind.RESTORE,
                    snapshot=round_.before,
                    title=f"가정 종료 · {cell}",
                    message=f"임시 가정을 제거하고 원본 상태로 돌아갑니다. {next_action}",
                    focus_cells=(result.assumption,),
                )
            )

    if round_.elimination is not None:
        _append_logic_steps(
            frames,
            round_.elimination,
        )


def _solution_snapshot(result: SolveResult) -> LogicSnapshot | None:
    if result.solution is None:
        return None
    puzzle = result.initial_logic_result.initial_state.puzzle
    cats = frozenset(result.solution)
    status_grid = tuple(
        tuple(
            CellState.CAT if (row, column) in cats else CellState.EXCLUDED
            for column in range(puzzle.size)
        )
        for row in range(puzzle.size)
    )
    return LogicSnapshot(puzzle, status_grid)


def _final_frame(result: SolveResult, snapshot: LogicSnapshot) -> PlaybackFrame:
    if result.exact_result.status is ExactStatus.MULTIPLE:
        title = "최종 결과 · 복수해"
        method = _SEARCH_LABEL if result.used_backtrack_search else _PROBING_LABEL
        message = f"{method}으로 찾은 첫 해를 표시합니다. 다른 해도 존재합니다."
    elif result.exact_result.status is ExactStatus.UNSOLVABLE:
        title = "최종 결과 · 해 없음"
        if result.used_backtrack_search:
            message = (
                f"{_PROBING_LABEL}에서 결론을 내지 못해 {_SEARCH_LABEL}했지만 "
                "유효한 해가 없습니다."
            )
        else:
            terminal_logic = result.initial_logic_result
            if result.probing_rounds:
                elimination = result.probing_rounds[-1].elimination
                if elimination is not None:
                    terminal_logic = elimination
            message = terminal_logic.message
    elif result.outcome is SolveOutcome.SOLVED_WITH_BACKTRACK_SEARCH:
        title = "최종 결과 · 유일해"
        message = (
            f"{_PROBING_LABEL}이 막힌 상태에서 {_SEARCH_LABEL}으로 해를 찾았습니다."
        )
    elif result.outcome is SolveOutcome.SOLVED_WITH_PROBING:
        title = "최종 결과 · 유일해"
        message = f"{_PROBING_LABEL} 과정에서 해를 찾았습니다."
    else:
        title = "최종 결과 · 유일해"
        message = "결정적 추론만으로 해결했습니다."
    return PlaybackFrame(
        kind=TimelineKind.FINAL,
        snapshot=snapshot,
        title=title,
        message=message,
        focus_cells=tuple(result.solution or ()),
    )


def build_timeline(result: SolveResult) -> tuple[PlaybackFrame, ...]:
    """저장된 결정적 추론과 한 단계 가정을 재생 프레임으로 만든다."""

    initial = result.initial_logic_result
    frames = [
        PlaybackFrame(
            kind=TimelineKind.START,
            snapshot=initial.initial_state,
            title="풀이 시작",
            message="빈 보드에서 결정적 추론을 시작합니다.",
        )
    ]
    _append_logic_steps(frames, initial)
    frames.append(
        PlaybackFrame(
            kind=TimelineKind.LOGIC_END,
            snapshot=initial.final_state,
            title=_LOGIC_END_TITLES[initial.status],
            message=initial.message,
            region_indices=(
                _empty_region_indices(initial.final_state)
                if initial.status is LogicStatus.CONTRADICTION
                else ()
            ),
        )
    )

    for round_ in result.probing_rounds:
        _append_probing_round(frames, round_)

    if result.used_backtrack_search:
        last_round = result.probing_rounds[-1]
        if last_round.candidates:
            search_message = (
                "새 고양이를 즉시 확정하는 후보들을 한 번씩 가정해도 "
                "결론이 없었습니다. 임시 가정이 없는 현재 상태에서 "
                f"{_SEARCH_LABEL}으로 답 하나를 찾습니다."
            )
        else:
            search_message = (
                "한 단계 가정의 실행 조건을 만족하는 후보가 없습니다. "
                f"현재 상태에서 {_SEARCH_LABEL}으로 답 하나를 찾습니다."
            )
        frames.append(
            PlaybackFrame(
                kind=TimelineKind.BACKTRACK_SEARCH,
                snapshot=last_round.before,
                title=_SEARCH_LABEL,
                message=search_message,
                focus_cells=last_round.candidates,
            )
        )

    final_snapshot = _solution_snapshot(result) or frames[-1].snapshot
    frames.append(_final_frame(result, final_snapshot))
    return tuple(frames)

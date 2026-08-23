"""기본 로직과 귀류법 기록을 화면 재생용 프레임으로 변환한다."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .exact_solver import ExactStatus
from .model import Cell
from .solve_types import (
    TECHNIQUE_LABELS,
    LogicResult,
    LogicStatus,
    LogicStep,
    Technique,
)
from .solver import AssumptionResult, RefutationRound, SolveOutcome, SolveResult
from .state import CellState, LogicSnapshot


class TimelineKind(StrEnum):
    """재생 화면에서 구분하는 프레임 종류."""

    START = "start"
    LOGIC_STEP = "logic_step"
    LOGIC_END = "logic_end"
    REFUTATION_SELECT = "refutation_select"
    ASSUME = "assume"
    ASSUMPTION_END = "assumption_end"
    RESTORE = "restore"
    BACKTRACKING = "backtracking"
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
    logic_step: LogicStep | None = None


_LOGIC_END_TITLES = {
    LogicStatus.SOLVED_LOGICALLY: "기본 로직 완료",
    LogicStatus.STALLED: "기본 로직 정체",
    LogicStatus.CONTRADICTION: "기본 로직 모순",
}

_ASSUMPTION_END_TITLES = {
    LogicStatus.SOLVED_LOGICALLY: "가정 결과 해결",
    LogicStatus.STALLED: "가정 결과 정체",
    LogicStatus.CONTRADICTION: "가정 결과 모순",
}


def _cell_name(cell: Cell) -> str:
    return f"R{cell[0] + 1}C{cell[1] + 1}"


def _cells_text(cells: tuple[Cell, ...]) -> str:
    return ", ".join(_cell_name(cell) for cell in cells)


def _unit_name(round_: RefutationRound) -> str:
    ref = round_.selected_unit
    if ref.kind.value == "row":
        return f"행 {ref.index + 1}"
    if ref.kind.value == "column":
        return f"열 {ref.index + 1}"
    return f"영역 {round_.before.puzzle.region_labels[ref.index]}"


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


def _append_logic_steps(
    frames: list[PlaybackFrame],
    result: LogicResult,
    *,
    context: str,
    active_assumption: Cell | None = None,
) -> None:
    for step in result.steps:
        label = TECHNIQUE_LABELS[step.deduction.technique]
        if step.deduction.technique is Technique.REFUTATION_ELIMINATION:
            title = f"귀류법 확정 · {_cell_name(step.deduction.exclusions[0])} = X"
        else:
            title = f"{context} {step.number}단계 · {label}"
        frames.append(
            PlaybackFrame(
                kind=TimelineKind.LOGIC_STEP,
                snapshot=step.after,
                title=title,
                message=step.deduction.explanation or f"{label}을 적용했습니다.",
                active_assumption=active_assumption,
                focus_cells=_step_focus(step),
                logic_step=step,
            )
        )


def _assumption_message(result: AssumptionResult) -> str:
    cell = _cell_name(result.assumption)
    if result.status is LogicStatus.CONTRADICTION:
        detail = result.logic_result.message or "가능한 배치 조건이 깨졌습니다."
        return f"{cell}에 고양이를 놓으면 모순입니다. {detail}"
    if result.status is LogicStatus.SOLVED_LOGICALLY:
        return f"{cell}을 가정한 뒤 기본 로직만으로 완성했습니다."
    return f"{cell} 가정에서 기본 로직이 더 진행되지 않습니다."


def _append_refutation_round(
    frames: list[PlaybackFrame],
    round_: RefutationRound,
) -> None:
    unit_name = _unit_name(round_)
    frames.append(
        PlaybackFrame(
            kind=TimelineKind.REFUTATION_SELECT,
            snapshot=round_.before,
            title=f"귀류법 · {unit_name} 후보 선택",
            message=(
                f"후보가 가장 적은 {unit_name}을 선택했습니다. 이 단위의 "
                "후보만 하나씩 가정하며, 가정 안에서 다른 가정은 하지 "
                "않습니다. "
                f"후보: {_cells_text(round_.candidates)}"
            ),
            focus_cells=round_.candidates,
        )
    )

    for index, result in enumerate(round_.assumptions, start=1):
        cell = _cell_name(result.assumption)
        frames.append(
            PlaybackFrame(
                kind=TimelineKind.ASSUME,
                snapshot=result.logic_result.initial_state,
                title=f"귀류법 가정 {index}/{len(round_.candidates)} · {cell}",
                message=(f"{cell}에 고양이를 가정하고 기본 로직을 끝까지 적용합니다."),
                active_assumption=result.assumption,
                focus_cells=(result.assumption,),
            )
        )
        _append_logic_steps(
            frames,
            result.logic_result,
            context=f"{cell} 가정",
            active_assumption=result.assumption,
        )
        frames.append(
            PlaybackFrame(
                kind=TimelineKind.ASSUMPTION_END,
                snapshot=result.logic_result.final_state,
                title=f"{_ASSUMPTION_END_TITLES[result.status]} · {cell}",
                message=_assumption_message(result),
                active_assumption=result.assumption,
                focus_cells=(result.assumption,),
            )
        )
        if result.status is not LogicStatus.SOLVED_LOGICALLY:
            next_action = (
                f"모순이므로 {cell}을 X로 확정합니다."
                if result.status is LogicStatus.CONTRADICTION
                else "결론이 없어 선택한 단위의 다음 후보로 넘어갑니다."
            )
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
            context="X 반영 후 기본 로직",
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
        method = "백트래킹" if result.used_backtracking else "귀류법"
        message = f"{method}으로 찾은 첫 해를 표시합니다. 다른 해도 존재합니다."
    elif result.exact_result.status is ExactStatus.UNSOLVABLE:
        title = "최종 결과 · 해 없음"
        if result.used_backtracking:
            message = "귀류법에서 결론을 내지 못해 백트래킹했지만 유효한 해가 없습니다."
        else:
            terminal_logic = result.initial_logic_result
            if result.refutation_rounds:
                elimination = result.refutation_rounds[-1].elimination
                if elimination is not None:
                    terminal_logic = elimination
            message = terminal_logic.message
    elif result.outcome is SolveOutcome.SOLVED_WITH_BACKTRACKING:
        title = "최종 결과 · 유일해"
        message = "귀류법이 막힌 상태에서 백트래킹으로 해를 찾았습니다."
    elif result.outcome is SolveOutcome.SOLVED_WITH_REFUTATION:
        title = "최종 결과 · 유일해"
        message = "귀류법으로 해를 찾았습니다."
    else:
        title = "최종 결과 · 유일해"
        message = "기본 로직만으로 해결했습니다."
    return PlaybackFrame(
        kind=TimelineKind.FINAL,
        snapshot=snapshot,
        title=title,
        message=message,
        focus_cells=tuple(result.solution or ()),
    )


def build_timeline(result: SolveResult) -> tuple[PlaybackFrame, ...]:
    """저장된 기본 로직과 귀류법 과정을 재생 프레임으로 만든다."""

    initial = result.initial_logic_result
    frames = [
        PlaybackFrame(
            kind=TimelineKind.START,
            snapshot=initial.initial_state,
            title="풀이 시작",
            message="빈 보드에서 기본 로직을 시작합니다.",
        )
    ]
    _append_logic_steps(frames, initial, context="기본 로직")
    frames.append(
        PlaybackFrame(
            kind=TimelineKind.LOGIC_END,
            snapshot=initial.final_state,
            title=_LOGIC_END_TITLES[initial.status],
            message=initial.message,
        )
    )

    for round_ in result.refutation_rounds:
        _append_refutation_round(frames, round_)

    if result.used_backtracking:
        frames.append(
            PlaybackFrame(
                kind=TimelineKind.BACKTRACKING,
                snapshot=result.refutation_rounds[-1].before,
                title="귀류법 종료 · 백트래킹 시작",
                message=(
                    "선택한 단위의 모든 후보를 한 번씩 가정해도 정체했습니다. "
                    "임시 가정이 없는 현재 상태에서 "
                    "백트래킹으로 답 하나를 찾습니다."
                ),
                focus_cells=result.refutation_rounds[-1].candidates,
            )
        )

    final_snapshot = _solution_snapshot(result) or frames[-1].snapshot
    frames.append(_final_frame(result, final_snapshot))
    return tuple(frames)

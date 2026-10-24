"""Korean descriptions for one native Sudoku playback frame."""

from puzzle_common.coordinates import cell_name as _cell_name
from puzzle_common.engine import LogicStatus, Outcome, SolveResult
from puzzle_common.presentation import FrameKind, PlaybackFrame
from puzzle_common.ui_style import ACCENT, ORANGE
from puzzle_common.view import PlaybackDetails

from .solve_types import (
    ContradictionKind,
    ContradictionWitness,
    Technique,
    TechniqueResult,
)
from .topology import COLS, ROWS

_TECHNIQUE_LABELS: dict[Technique, str] = {
    Technique.FULL_HOUSE: "Full House",
    Technique.NAKED_SINGLE: "Naked Single",
    Technique.HIDDEN_SINGLE: "Hidden Single",
    Technique.LOCKED_PAIR: "Locked Pair",
    Technique.NAKED_PAIR: "Naked Pair",
    Technique.LOCKED_CANDIDATES_POINTING: "Locked Candidates — Pointing",
    Technique.LOCKED_CANDIDATES_CLAIMING: "Locked Candidates — Claiming",
    Technique.LOCKED_TRIPLE: "Locked Triple",
    Technique.NAKED_TRIPLE: "Naked Triple",
    Technique.HIDDEN_PAIR: "Hidden Pair",
    Technique.HIDDEN_TRIPLE: "Hidden Triple",
    Technique.REFUTATION: "귀류법",
}


def _deduction_effect_groups(
    deduction: TechniqueResult,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return labeled, atomic effect items from structured deduction data."""

    groups: list[tuple[str, tuple[str, ...]]] = []
    if deduction.assignments:
        items = tuple(
            dict.fromkeys(
                f"{_cell_name(item.cell)} = {item.value}"
                for item in deduction.assignments
            )
        )
        groups.append((f"확정 칸 · {len(items)}", items))
    if deduction.eliminations:
        items = tuple(
            dict.fromkeys(
                f"{_cell_name(item.cell)}: {', '.join(map(str, sorted(item.values)))}"
                for item in deduction.eliminations
            )
        )
        groups.append((f"후보 제거 · {len(items)}", items))
    return tuple(groups)


def _technique_label(frame: PlaybackFrame) -> str:
    """Return the technique label, including the final Full House special case."""

    deduction = frame.deduction
    if deduction is None:
        raise ValueError("논리 기법 라벨에는 deduction이 필요합니다.")
    if (
        deduction.technique is Technique.FULL_HOUSE
        and len(deduction.assignments) == 1
        and all(value != 0 for row in frame.snapshot[0] for value in row)
    ):
        return "Last Digit"
    return _TECHNIQUE_LABELS[deduction.technique]


def _contradiction_message(witness: ContradictionWitness) -> str:
    if witness.kind is ContradictionKind.EMPTY_CELL and len(witness.cells) == 1:
        cell = witness.cells[0]
        return (
            f"모순을 발견했습니다. R{cell[0] + 1}C{cell[1] + 1}에 남은 후보가 없습니다."
        )

    if (
        witness.kind is ContradictionKind.MISSING_DIGIT
        and witness.unit_index is not None
        and len(witness.digits) == 1
    ):
        unit_name = _unit_name(witness.unit_index)
        value = min(witness.digits)
        return (
            f"모순을 발견했습니다. {unit_name}에 숫자 {value}가 들어갈 곳이 없습니다."
        )

    raise RuntimeError("구조가 잘못된 모순 witness입니다.")


def _unit_name(unit_index: int) -> str:
    if unit_index < len(ROWS):
        return f"{unit_index + 1}행"
    if unit_index < len(ROWS) + len(COLS):
        return f"{unit_index - len(ROWS) + 1}열"
    return f"{unit_index - len(ROWS) - len(COLS) + 1}번 박스"


def describe_frame(frame: PlaybackFrame, result: SolveResult) -> PlaybackDetails:
    """Describe one canonical event without converting or traversing the run."""
    decision = frame.assumption
    assumption = (
        f"{_cell_name(decision.cell)} = {decision.value}"
        if decision is not None
        else ""
    )
    if frame.kind is FrameKind.START:
        title, reason = "초기 상태", "초기 후보 상태"
    elif frame.kind is FrameKind.DEDUCTION:
        title, reason = "논리 기법", frame.deduction.explanation
    elif frame.kind is FrameKind.REFUTATION:
        title, reason = "귀류 결론", frame.deduction.explanation
    elif frame.kind is FrameKind.PROBING_SELECT:
        title = "가정 후보 선택"
        reason = (
            f"현재 2후보 셀의 가정 {len(frame.candidates)}개를 H1 점수 순으로 살펴봅니다. "
            "같은 점수에서는 정체된 가정보다 새 가정을 먼저 시도합니다."
            if frame.candidates
            else "2후보 셀이 없어 한 단계 가정을 시도할 수 없습니다."
        )
    elif frame.kind is FrameKind.PROBE_START:
        title = "한 단계 가정"
        reason = (
            f"2후보 셀 가정: {assumption}로 두고 추가 가정 없이 기존 논리만 적용합니다."
        )
    elif frame.kind is FrameKind.PROBE_END and frame.status is LogicStatus.SOLVED:
        title = "가정에서 해 발견"
        reason = f"{assumption} 가정에서 추가 가정 없이 해 하나를 완성했습니다."
    elif frame.kind is FrameKind.PROBE_END and frame.status is LogicStatus.STALLED:
        title = "가정 정체"
        reason = (
            f"{assumption} 가정에서는 모순도 완성도 나오지 않아 원래 상태로 돌아갑니다."
        )
    elif frame.kind is FrameKind.RESTORE:
        title = "원래 상태 복원"
        reason = f"{assumption} 가정을 마치고 원래 후보 상태로 돌아갑니다."
    elif frame.kind in (FrameKind.LOGIC_END, FrameKind.PROBE_END):
        if frame.contradiction is not None:
            title, reason = "모순", _contradiction_message(frame.contradiction)
        elif frame.status is LogicStatus.SOLVED:
            title = "논리 완료"
            reason = "기존 논리를 적용해 해 하나를 완성했습니다."
        else:
            title = "논리 정체"
            reason = "현재 구현된 논리 기법으로 더 진행할 수 없습니다."
    elif frame.kind is FrameKind.SEARCH:
        title = "백트래킹 전환"
        reason = (
            "2후보 셀이 없거나 모든 2후보 가정이 정체되어, "
            "여기부터는 MRV 백트래킹으로 전환합니다."
        )
    elif result.outcome is Outcome.UNSOLVABLE:
        title, reason = "해 없음", "현재 단서로 가능한 해가 없습니다."
    else:
        title = "풀이 완료"
        reason = (
            "해가 둘 이상 존재합니다. 표시한 보드는 가능한 해 중 하나입니다."
            if result.outcome is Outcome.MULTIPLE
            else "유일한 해를 확인했습니다."
        )
    annotations = []
    if frame.deduction is not None:
        annotations.append((_technique_label(frame), ACCENT))
    if frame.active_assumption is not None:
        annotations.append(("한 단계 가정 중", ORANGE))
    return PlaybackDetails(
        title=title,
        reason=reason,
        effects=_deduction_effect_groups(frame.deduction)
        if frame.deduction is not None
        else (),
        annotations=tuple(annotations),
        assumption=assumption if frame.active_assumption is not None else "",
    )

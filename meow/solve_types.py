"""결정적 추론 솔버가 공유하는 불변 값 객체.

기법 finder는 :class:`Deduction`만 만들고 상태를 바꾸지 않는다. 실제 적용과
단계 기록은 ``logic_solver``가 담당한다. 이 분리 덕분에 각 추론의 근거와
효과를 독립적으로 검사할 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from .model import Cell

if TYPE_CHECKING:
    from .state import LogicSnapshot


class LogicStatus(StrEnum):
    """논리 풀이의 가능한 종료 상태."""

    SOLVED_LOGICALLY = "SOLVED_LOGICALLY"
    STALLED = "STALLED"
    CONTRADICTION = "CONTRADICTION"


class UnitKind(StrEnum):
    """퍼즐의 세 가지 exact-one 단위."""

    ROW = "row"
    COLUMN = "column"
    REGION = "region"


@dataclass(frozen=True, slots=True, order=True)
class UnitRef:
    """trace에서 행·열·영역을 안정적으로 가리키는 참조."""

    kind: UnitKind
    index: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError("단위 인덱스는 0 이상이어야 합니다.")


class SolverAlgorithm(StrEnum):
    """솔버를 구성하는 내부 알고리즘의 안정적인 이름."""

    DIRECT_PROPAGATION = "direct_propagation"
    UNIT_SUPPORT = "unit_support"
    CONTAINER_MATCHING = "container_matching"
    SINGLETON_PROBING = "singleton_probing"
    BACKTRACK_SEARCH = "backtrack_search"


SOLVER_ALGORITHM_LABELS: Final[dict[SolverAlgorithm, str]] = {
    SolverAlgorithm.DIRECT_PROPAGATION: "Basic Deductions",
    SolverAlgorithm.CONTAINER_MATCHING: "Container Locks",
    SolverAlgorithm.UNIT_SUPPORT: "Crowding",
    SolverAlgorithm.SINGLETON_PROBING: "One-Step Lookahead",
    SolverAlgorithm.BACKTRACK_SEARCH: "Backtracking",
}


class Technique(StrEnum):
    """상위 알고리즘 안에서 설명에 사용하는 세부 추론 기법."""

    PLACED_CAT_ELIMINATION = "placed_cat_elimination"
    ROW_SINGLE = "row_single"
    COLUMN_SINGLE = "column_single"
    REGION_SINGLE = "region_single"
    REGION_TO_ROW_LOCK = "region_to_row_lock"
    REGION_TO_COLUMN_LOCK = "region_to_column_lock"
    ROW_TO_REGION_LOCK = "row_to_region_lock"
    COLUMN_TO_REGION_LOCK = "column_to_region_lock"
    UNIT_SUPPORT = "unit_support"
    HALL_LOCK = "hall_lock"
    PROBE_ELIMINATION = "probe_elimination"


TECHNIQUE_LABELS: Final[dict[Technique, str]] = {
    Technique.PLACED_CAT_ELIMINATION: "배치된 고양이의 충돌 제거",
    Technique.ROW_SINGLE: "행 Single",
    Technique.COLUMN_SINGLE: "열 Single",
    Technique.REGION_SINGLE: "영역 Single",
    Technique.REGION_TO_ROW_LOCK: "영역→행 잠금",
    Technique.REGION_TO_COLUMN_LOCK: "영역→열 잠금",
    Technique.ROW_TO_REGION_LOCK: "행→영역 잠금",
    Technique.COLUMN_TO_REGION_LOCK: "열→영역 잠금",
    Technique.UNIT_SUPPORT: "단위 막힘",
    Technique.HALL_LOCK: "Hall 잠금",
    Technique.PROBE_ELIMINATION: "한 단계 가정으로 후보 제외",
}


TECHNIQUE_ALGORITHMS: Final[dict[Technique, SolverAlgorithm]] = {
    Technique.PLACED_CAT_ELIMINATION: SolverAlgorithm.DIRECT_PROPAGATION,
    Technique.ROW_SINGLE: SolverAlgorithm.DIRECT_PROPAGATION,
    Technique.COLUMN_SINGLE: SolverAlgorithm.DIRECT_PROPAGATION,
    Technique.REGION_SINGLE: SolverAlgorithm.DIRECT_PROPAGATION,
    Technique.UNIT_SUPPORT: SolverAlgorithm.UNIT_SUPPORT,
    Technique.REGION_TO_ROW_LOCK: SolverAlgorithm.CONTAINER_MATCHING,
    Technique.REGION_TO_COLUMN_LOCK: SolverAlgorithm.CONTAINER_MATCHING,
    Technique.ROW_TO_REGION_LOCK: SolverAlgorithm.CONTAINER_MATCHING,
    Technique.COLUMN_TO_REGION_LOCK: SolverAlgorithm.CONTAINER_MATCHING,
    Technique.HALL_LOCK: SolverAlgorithm.CONTAINER_MATCHING,
    Technique.PROBE_ELIMINATION: SolverAlgorithm.SINGLETON_PROBING,
}


@dataclass(frozen=True, slots=True)
class Deduction:
    """아직 적용하지 않은 하나의 원자적 논리 추론.

    ``placements``와 ``exclusions``가 상태에 가할 적용 내역(delta)이다.
    ``explanation``은 그 적용을 정당화하는 사유만 담고, 나머지 필드는
    UI가 사유와 적용 내역을 표시할 때 쓰는 구조화된 근거다. 영역 이름은
    사용자에게 노출하지 않고 ``evidence_units``로 실제 색상을 표시한다.
    """

    technique: Technique
    placements: tuple[Cell, ...] = ()
    exclusions: tuple[Cell, ...] = ()
    evidence_cells: tuple[Cell, ...] = ()
    evidence_units: tuple[UnitRef, ...] = ()
    explanation: str = ""

    def __post_init__(self) -> None:
        if not self.placements and not self.exclusions:
            raise ValueError("추론에는 배치 또는 제외 효과가 있어야 합니다.")
        if len(set(self.placements)) != len(self.placements):
            raise ValueError("placements에 같은 칸이 중복되었습니다.")
        if len(set(self.exclusions)) != len(self.exclusions):
            raise ValueError("exclusions에 같은 칸이 중복되었습니다.")
        if len(set(self.evidence_units)) != len(self.evidence_units):
            raise ValueError("evidence_units에 같은 단위가 중복되었습니다.")
        overlap = set(self.placements) & set(self.exclusions)
        if overlap:
            raise ValueError(
                f"같은 칸을 배치와 제외에 함께 넣을 수 없습니다: {overlap}"
            )

    @property
    def algorithm(self) -> SolverAlgorithm:
        """이 세부 추론을 만든 상위 알고리즘을 반환한다."""

        return TECHNIQUE_ALGORITHMS[self.technique]


@dataclass(frozen=True, slots=True)
class LogicStep:
    """추론 적용 전후의 상태를 함께 보존하는 한 단계."""

    number: int
    deduction: Deduction
    before: LogicSnapshot
    after: LogicSnapshot

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("단계 번호는 1부터 시작해야 합니다.")


@dataclass(frozen=True, slots=True)
class LogicResult:
    """정답 탐색을 섞지 않은 논리 풀이 결과와 전체 trace."""

    status: LogicStatus
    initial_state: LogicSnapshot
    final_state: LogicSnapshot
    steps: tuple[LogicStep, ...]
    message: str = ""

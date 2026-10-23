"""솔버·기법·화면이 공유하는 불변 값 객체."""

from dataclasses import dataclass
from enum import StrEnum

from .board import Grid
from .topology import Cell

type CandidateGrid = tuple[tuple[frozenset[int], ...], ...]


class SolveStatus(StrEnum):
    """구조가 유효한 퍼즐의 세 가지 풀이 결과."""

    SOLVED_UNIQUE = "solved_unique"
    SOLVED_MULTIPLE = "solved_multiple"
    UNSOLVABLE = "unsolvable"


class StepKind(StrEnum):
    """풀이 기록 화면에서 사용하는 단계 종류."""

    INITIAL_STATE = "initial_state"
    TECHNIQUE = "technique"
    ASSUMPTION = "assumption"
    ASSUMPTION_STALLED = "assumption_stalled"
    ASSUMPTION_SOLVED = "assumption_solved"
    CONTRADICTION = "contradiction"
    REFUTATION = "refutation"
    SEARCH_FALLBACK = "search_fallback"
    SOLVED = "solved"
    UNSOLVABLE = "unsolvable"


class Technique(StrEnum):
    """사람식 솔버에 구현된 논리 추론 기법."""

    FULL_HOUSE = "full_house"
    NAKED_SINGLE = "naked_single"
    HIDDEN_SINGLE = "hidden_single"
    LOCKED_PAIR = "locked_pair"
    NAKED_PAIR = "naked_pair"
    LOCKED_CANDIDATES_POINTING = "locked_candidates_pointing"
    LOCKED_CANDIDATES_CLAIMING = "locked_candidates_claiming"
    LOCKED_TRIPLE = "locked_triple"
    NAKED_TRIPLE = "naked_triple"
    HIDDEN_PAIR = "hidden_pair"
    HIDDEN_TRIPLE = "hidden_triple"
    REFUTATION = "refutation"


class ContradictionKind(StrEnum):
    """솔버 상태가 제공하는 구조화된 모순 종류."""

    EMPTY_CELL = "empty_cell"
    MISSING_DIGIT = "missing_digit"


@dataclass(frozen=True, slots=True)
class Assignment:
    """칸 하나에 확정한 값 하나."""

    cell: Cell
    value: int


@dataclass(frozen=True, slots=True)
class Elimination:
    """논리 추론으로 칸 하나에서 제거한 후보 값."""

    cell: Cell
    values: frozenset[int]


@dataclass(frozen=True, slots=True)
class TechniqueResult:
    """고정된 상태 하나에서 도출한 미적용 논리 배치.

    ``explanation``에는 이유만 담는다. 표시 대상은 ``assignments``와
    ``eliminations``에서 가져와 설명과 효과가 어긋나거나 반복되지 않게 한다."""

    technique: Technique
    assignments: tuple[Assignment, ...] = ()
    eliminations: tuple[Elimination, ...] = ()
    evidence_cells: tuple[Cell, ...] = ()
    context_cells: tuple[Cell, ...] = ()
    explanation: str = ""

    @property
    def has_changes(self) -> bool:
        return bool(self.assignments or self.eliminations)


@dataclass(frozen=True, slots=True)
class ContradictionWitness:
    """모순 하나를 증명하는 고정된 칸·하우스·숫자."""

    kind: ContradictionKind
    cells: tuple[Cell, ...] = ()
    unit_index: int | None = None
    digits: frozenset[int] = frozenset()


@dataclass(frozen=True, slots=True)
class SolveStep:
    """상태 스냅샷 하나만 담는 불변 풀이 기록."""

    kind: StepKind
    grid: Grid
    candidates: CandidateGrid
    deduction: TechniqueResult | None = None
    assumption: Assignment | None = None
    contradiction: ContradictionWitness | None = None
    message: str = ""

    @property
    def depth(self) -> int:
        """활성 가정 수이며, 사람식 풀이 기록에서는 1을 넘지 않는다."""

        return int(self.assumption is not None and self.kind is not StepKind.REFUTATION)


@dataclass(frozen=True, slots=True)
class SolveResult:
    """유효한 퍼즐 하나의 최종 결과와 불변 풀이 기록."""

    status: SolveStatus
    steps: tuple[SolveStep, ...]

    @property
    def solution(self) -> Grid | None:
        """해가 있으면 대표 해를 반환한다."""

        if self.status is SolveStatus.UNSOLVABLE:
            return None
        return self.steps[-1].grid

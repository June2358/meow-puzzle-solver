"""Immutable value objects shared by the solver, techniques, and views."""

from dataclasses import dataclass
from enum import StrEnum

from .board import Grid
from .topology import Cell

type CandidateGrid = tuple[tuple[frozenset[int], ...], ...]


class SolveStatus(StrEnum):
    """The three meaningful outcomes for a structurally valid puzzle."""

    SOLVED_UNIQUE = "solved_unique"
    SOLVED_MULTIPLE = "solved_multiple"
    UNSOLVABLE = "unsolvable"


class StepKind(StrEnum):
    """Semantic categories consumed by the solve-trace view."""

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
    """Logical deductions currently implemented by the human-style solver."""

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
    """Structured contradiction categories emitted by the solver state."""

    EMPTY_CELL = "empty_cell"
    MISSING_DIGIT = "missing_digit"


@dataclass(frozen=True, slots=True)
class Assignment:
    """One value placed in one cell."""

    cell: Cell
    value: int


@dataclass(frozen=True, slots=True)
class Elimination:
    """Candidate values removed from one cell by a logical deduction."""

    cell: Cell
    values: frozenset[int]


@dataclass(frozen=True, slots=True)
class TechniqueResult:
    """One unapplied logical wave derived from a single frozen state.

    ``explanation`` contains reason prose only. Presentation targets must come
    from ``assignments`` and ``eliminations`` so they cannot drift or repeat.
    """

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
    """The stable cells, house, and digits that prove one contradiction."""

    kind: ContradictionKind
    cells: tuple[Cell, ...] = ()
    unit_index: int | None = None
    digits: frozenset[int] = frozenset()


@dataclass(frozen=True, slots=True)
class SolveStep:
    """One immutable trace item containing exactly one state snapshot."""

    kind: StepKind
    grid: Grid
    candidates: CandidateGrid
    deduction: TechniqueResult | None = None
    assumption: Assignment | None = None
    contradiction: ContradictionWitness | None = None
    message: str = ""

    @property
    def depth(self) -> int:
        """Number of active assumptions; the human trace never exceeds one."""

        return int(self.assumption is not None and self.kind is not StepKind.REFUTATION)


@dataclass(frozen=True, slots=True)
class SolveResult:
    """Final outcome and immutable trace for one valid puzzle."""

    status: SolveStatus
    steps: tuple[SolveStep, ...]

    @property
    def solution(self) -> Grid | None:
        """Return the representative solution, if one exists."""

        if self.status is SolveStatus.UNSOLVABLE:
            return None
        return self.steps[-1].grid

"""Immutable value objects shared by the solver, techniques, and views."""

from dataclasses import dataclass
from enum import StrEnum

from .topology import Cell

type CandidateGrid = tuple[tuple[frozenset[int], ...], ...]


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

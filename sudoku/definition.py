"""Sudoku rules and native trace data for the common app."""

from puzzle_common.catalog import load_catalog
from puzzle_common.json_input import decode_json
from puzzle_common.presentation import FrameKind, PlaybackFrame
from puzzle_common.puzzle import PuzzleDefinition
from puzzle_common.view import FrameData, Grid

from .board import InvalidBoardError, Puzzle, find_conflicting_cells, validate_grid
from .solve_types import (
    Assignment,
    ContradictionKind,
    ContradictionWitness,
    Technique,
    TechniqueResult,
)
from .solver import solve as solve_native
from .topology import COLS, ROWS, SIZE, UNITS

REGIONS = tuple(
    tuple((row // 3) * 3 + column // 3 for column in range(SIZE)) for row in range(SIZE)
)
_TECHNIQUE_LABELS = {
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


OCR_MATRIX_PROMPT = """Transcribe the Sudoku puzzle in the attached image.

Rules:
1. Do not solve the puzzle or infer any missing digit.
2. Read cells from top to bottom and left to right.
3. Copy only clearly visible fixed/given digits.
4. Use 0 for every blank or unreadable cell.
5. Ignore pencil marks, candidate notes, highlights, and surrounding text.
6. Return exactly one 9x9 JSON array of integers from 0 to 9.
7. Return raw JSON only: no explanation, Markdown code fence, or object wrapper.

The following example demonstrates the output format only. Do not copy its
digits unless they are actually visible in the attached image.

Example visible grid:
53..7....
6..195...
.98....6.
8...6...3
4..8.3..1
7...2...6
.6....28.
...419..5
....8..79

Required example output:
[
  [5, 3, 0, 0, 7, 0, 0, 0, 0],
  [6, 0, 0, 1, 9, 5, 0, 0, 0],
  [0, 9, 8, 0, 0, 0, 0, 6, 0],
  [8, 0, 0, 0, 6, 0, 0, 0, 3],
  [4, 0, 0, 8, 0, 3, 0, 0, 1],
  [7, 0, 0, 0, 2, 0, 0, 0, 6],
  [0, 6, 0, 0, 0, 0, 2, 8, 0],
  [0, 0, 0, 4, 1, 9, 0, 0, 5],
  [0, 0, 0, 0, 8, 0, 0, 7, 9]
]"""


class MatrixParseError(ValueError):
    """Raised when AI/OCR JSON is not one raw 9x9 integer matrix."""


def parse_matrix_json(text: str) -> Grid:
    """Parse a raw JSON 9x9 integer array without applying Sudoku rules."""

    decoded = decode_json(text, MatrixParseError)

    if type(decoded) is not list:
        raise MatrixParseError("최상위 JSON 값은 9개 행을 가진 배열이어야 합니다.")
    if any(type(row) is not list for row in decoded):
        raise MatrixParseError("JSON의 각 행은 배열이어야 합니다.")

    try:
        return validate_grid(decoded)
    except InvalidBoardError as exc:
        raise MatrixParseError(str(exc)) from exc


def _validate_preset(grid: object) -> Grid:
    puzzle = Puzzle(grid)
    if not puzzle.givens:
        raise InvalidBoardError("퍼즐에는 초기 단서가 없습니다.")
    return puzzle.grid


def load_puzzle_catalog():
    return load_catalog(__package__, _validate_preset)


def solve(grid: Grid):
    puzzle = Puzzle(grid)
    if not puzzle.givens:
        raise InvalidBoardError("최소 한 개 이상의 초기 숫자를 입력하세요.")
    return solve_native(puzzle)


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
        index = witness.unit_index
        unit_name = (
            f"{index + 1}행"
            if index < len(ROWS)
            else f"{index - len(ROWS) + 1}열"
            if index < len(ROWS) + len(COLS)
            else f"{index - len(ROWS) - len(COLS) + 1}번 박스"
        )
        return (
            f"모순을 발견했습니다. {unit_name}에 숫자 {min(witness.digits)}가 "
            "들어갈 곳이 없습니다."
        )
    raise RuntimeError("구조가 잘못된 모순 witness입니다.")


def frame_data(grid: Grid, frame: PlaybackFrame) -> FrameData:
    deduction = frame.deduction
    contradiction = frame.contradiction
    technique = ""
    if deduction is not None:
        technique = (
            "Last Digit"
            if deduction.technique is Technique.FULL_HOUSE
            and len(deduction.assignments) == 1
            and all(value != 0 for row in frame.snapshot[0] for value in row)
            else _TECHNIQUE_LABELS[deduction.technique]
        )
    return FrameData(
        source=frame.snapshot,
        values=frame.snapshot[0],
        candidates=frame.snapshot[1],
        placements=tuple((item.cell, item.value) for item in deduction.assignments)
        if deduction
        else (),
        eliminations=tuple(
            (item.cell, tuple(sorted(item.values))) for item in deduction.eliminations
        )
        if deduction
        else (),
        context=deduction.context_cells if deduction else (),
        evidence=deduction.evidence_cells if deduction else (),
        contradiction_context=UNITS[contradiction.unit_index]
        if contradiction is not None and contradiction.unit_index is not None
        else (),
        contradiction_cells=contradiction.cells if contradiction else (),
        decision=(frame.assumption.cell, frame.assumption.value)
        if frame.assumption is not None
        else None,
        technique=technique,
        reason=deduction.explanation if deduction else "",
        contradiction=_contradiction_message(contradiction) if contradiction else "",
    )


def validate_frame(grid: Grid, frame: PlaybackFrame) -> None:
    snapshot = frame.snapshot
    if (
        not isinstance(snapshot, tuple)
        or len(snapshot) != 2
        or any(
            not isinstance(board, tuple)
            or len(board) != SIZE
            or any(not isinstance(row, tuple) or len(row) != SIZE for row in board)
            for board in snapshot
        )
    ):
        raise TypeError("스도쿠 grid/candidates가 필요합니다.")
    values, candidates = snapshot
    if any(
        type(value) is not int or not 0 <= value <= SIZE
        for row in values
        for value in row
    ):
        raise TypeError("스도쿠 grid는 0~9 정수로 구성되어야 합니다.")
    if any(
        not isinstance(values, frozenset)
        or any(type(value) is not int or not 1 <= value <= SIZE for value in values)
        for row in candidates
        for values in row
    ):
        raise TypeError("스도쿠 후보는 1~9 정수의 frozenset이어야 합니다.")
    if (
        frame.deduction is not None
        and not isinstance(frame.deduction, TechniqueResult)
        or frame.contradiction is not None
        and not isinstance(frame.contradiction, ContradictionWitness)
        or frame.assumption is not None
        and not isinstance(frame.assumption, Assignment)
        or any(not isinstance(decision, Assignment) for decision in frame.candidates)
    ):
        raise TypeError("스도쿠 추론과 가정이 필요합니다.")
    if frame.kind is FrameKind.START and values != grid:
        raise ValueError("풀이 결과가 전달된 문제에서 생성되지 않았습니다.")


DEFINITION = PuzzleDefinition(
    key="sudoku",
    title="스도쿠",
    symbols=tuple(range(1, 10)),
    empty=0,
    default_size=9,
    size_range=(9, 9),
    prompt=OCR_MATRIX_PROMPT,
    presets=load_puzzle_catalog(),
    normalize=validate_grid,
    parse=parse_matrix_json,
    solve=solve,
    frame_data=frame_data,
    validate_frame=validate_frame,
    regions=REGIONS,
    value_mark="text",
    value_label="",
    conflicts=find_conflicting_cells,
    probe_description=(
        "2후보 셀의 가정을 H1 점수 순으로 살펴봅니다. "
        "같은 점수에서는 정체된 가정보다 새 가정을 먼저 시도합니다."
    ),
)

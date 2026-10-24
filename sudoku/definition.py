"""Pure Sudoku semantics and projections for the common puzzle app."""

from puzzle_common.presentation import FrameKind, PlaybackFrame
from puzzle_common.puzzle import PuzzleDefinition
from puzzle_common.ui_style import (
    ACCENT,
    ACCENT_YELLOW,
    BLACK,
    CANDIDATE_GRAY,
    ORANGE,
    PRIMARY_DARK,
    PRIMARY_LIGHT,
    RED,
)
from puzzle_common.view import BoardView, CellMark, CellView

from .board import InvalidBoardError, Puzzle, find_conflicting_cells, validate_grid
from .matrix_input import OCR_MATRIX_PROMPT
from .matrix_parser import parse_matrix_json
from .presentation import describe_frame
from .puzzle_catalog import load_puzzle_catalog
from .solve_types import Assignment, ContradictionWitness, TechniqueResult
from .solver import SudokuSolver
from .topology import SIZE, UNITS

REGIONS = tuple(
    tuple((row // 3) * 3 + column // 3 for column in range(SIZE)) for row in range(SIZE)
)


def create(grid) -> Puzzle:
    puzzle = Puzzle(grid)
    if not puzzle.givens:
        raise InvalidBoardError("최소 한 개 이상의 초기 숫자를 입력하세요.")
    return puzzle


def editor_view(grid) -> BoardView:
    grid = validate_grid(grid)
    conflicts = find_conflicting_cells(grid)
    return BoardView(
        grid,
        tuple(
            tuple(
                CellView(
                    marks=(
                        CellMark(
                            text=str(value),
                            color=RED if (row_index, column) in conflicts else BLACK,
                        ),
                    )
                    if value
                    else (),
                    highlights=((*RED, 45),)
                    if (row_index, column) in conflicts
                    else (),
                )
                for column, value in enumerate(row)
            )
            for row_index, row in enumerate(grid)
        ),
        REGIONS,
    )


def frame_view(puzzle: Puzzle, frame: PlaybackFrame) -> BoardView:
    deduction = frame.deduction
    context = set(deduction.context_cells if deduction else ())
    evidence = set(deduction.evidence_cells if deduction else ())
    removed = (
        {item.cell: item.values for item in deduction.eliminations} if deduction else {}
    )
    assigned = {item.cell for item in deduction.assignments} if deduction else set()
    contradiction = frame.contradiction
    contradiction_context = (
        set(UNITS[contradiction.unit_index])
        if contradiction is not None and contradiction.unit_index is not None
        else set()
    )
    contradiction_cells = set(contradiction.cells if contradiction else ())
    active = (
        frame.active_assumption.cell if frame.active_assumption is not None else None
    )
    rows = []
    for row in range(SIZE):
        cells = []
        for column in range(SIZE):
            cell = (row, column)
            highlights = [
                color
                for group, color in (
                    (context, (*PRIMARY_LIGHT, 42)),
                    (contradiction_context, (*RED, 35)),
                    (evidence, (*ACCENT_YELLOW, 70)),
                    (removed, (*RED, 65)),
                    (assigned, (*ACCENT, 70)),
                    (contradiction_cells, (*RED, 80)),
                )
                if cell in group
            ]
            if (
                frame.assumption is not None
                and cell == frame.assumption.cell
                and (active is not None or frame.kind is FrameKind.REFUTATION)
            ):
                highlights.append(
                    (*(RED if frame.kind is FrameKind.REFUTATION else ORANGE), 80)
                )
            value = frame.snapshot[0][row][column]
            if value:
                color = (
                    BLACK
                    if cell in puzzle.givens
                    else ORANGE
                    if cell == active
                    else PRIMARY_DARK
                )
                marks = (CellMark(text=str(value), color=color),)
            else:
                candidates = frame.snapshot[1][row][column]
                eliminated = removed.get(cell, frozenset())
                marks = tuple(
                    CellMark(
                        text=str(value),
                        slot=value - 1,
                        color=RED if value in eliminated else CANDIDATE_GRAY,
                        struck=value in eliminated,
                    )
                    for value in range(1, SIZE + 1)
                    if value in candidates or value in eliminated
                )
            cells.append(
                CellView(
                    marks=marks,
                    highlights=tuple(highlights),
                    outline=ORANGE if cell == active else None,
                )
            )
        rows.append(tuple(cells))
    return BoardView(frame.snapshot, tuple(rows), REGIONS)


def validate_frames(puzzle: Puzzle, frames: tuple[PlaybackFrame, ...]) -> None:
    if not isinstance(puzzle, Puzzle):
        raise TypeError("스도쿠 정의는 Puzzle을 받아야 합니다.")
    if not frames:
        raise ValueError("풀이 기록이 비어 있습니다.")
    for frame in frames:
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
        grid, candidates = snapshot
        if any(
            type(value) is not int or not 0 <= value <= SIZE
            for row in grid
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
            or any(
                not isinstance(decision, Assignment) for decision in frame.candidates
            )
        ):
            raise TypeError("스도쿠 추론과 가정이 필요합니다.")
    if frames[0].snapshot[0] != puzzle.grid:
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
    create=create,
    solve=lambda puzzle: SudokuSolver(puzzle).solve(),
    grid=lambda puzzle: puzzle.grid,
    editor_view=editor_view,
    frame_view=frame_view,
    describe=describe_frame,
    validate_frames=validate_frames,
)

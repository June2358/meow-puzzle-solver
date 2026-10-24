"""Pure MEOW semantics and projections for the common puzzle app."""

from types import MappingProxyType

from puzzle_common.board import region_palette
from puzzle_common.presentation import PlaybackFrame
from puzzle_common.puzzle import PuzzleDefinition
from puzzle_common.ui_style import ACCENT, BLACK, GRAY, ORANGE, PRIMARY_DARK, RED, WHITE
from puzzle_common.view import BoardView, CellMark, CellView

from .input_draft import RegionDraft
from .matrix_input import VISION_REGION_PROMPT
from .model import Puzzle
from .parser import parse_puzzle_json
from .presentation import describe_frame
from .puzzle_catalog import PRESET_NAMES, load_preset
from .solve_types import Deduction
from .solver import solve
from .state import CellState, LogicSnapshot


def normalize(grid: object):
    return RegionDraft(grid).grid


def parse(text: str):
    return parse_puzzle_json(text).region_grid


def create(grid):
    return RegionDraft(grid).to_puzzle()


def editor_view(grid) -> BoardView:
    draft = RegionDraft(grid)
    colors = region_palette(draft.labels)
    return BoardView(
        grid,
        tuple(
            tuple(
                CellView(
                    background=colors.get(label, WHITE),
                    marks=(CellMark(text=label, color=BLACK),) if label else (),
                )
                for label in row
            )
            for row in draft.grid
        ),
        draft.grid,
    )


def frame_view(puzzle: Puzzle, frame: PlaybackFrame) -> BoardView:
    colors = region_palette(puzzle.region_labels)
    deduction = frame.deduction
    placements = set(deduction.placements if deduction else ())
    exclusions = set(deduction.exclusions if deduction else ())
    cells = []
    for row in range(puzzle.size):
        cells_row = []
        for column in range(puzzle.size):
            cell = (row, column)
            state = frame.snapshot.status_at(cell)
            marks = ()
            if state is CellState.CAT:
                color = (
                    ORANGE
                    if cell == frame.active_assumption
                    else ACCENT
                    if cell in placements
                    else PRIMARY_DARK
                )
                marks = (CellMark(kind="cat", color=color),)
            elif state is CellState.EXCLUDED:
                marks = (
                    CellMark(kind="cross", color=RED if cell in exclusions else GRAY),
                )
            cells_row.append(
                CellView(
                    background=colors[puzzle.region_label(cell)],
                    marks=marks,
                    outline=ORANGE if cell == frame.active_assumption else None,
                )
            )
        cells.append(tuple(cells_row))
    return BoardView(frame.snapshot, tuple(cells), puzzle.region_grid)


def validate_frames(puzzle: Puzzle, frames: tuple[PlaybackFrame, ...]) -> None:
    if not isinstance(puzzle, Puzzle):
        raise TypeError("MEOW 정의는 Puzzle을 받아야 합니다.")
    if not frames:
        raise ValueError("풀이 기록이 비어 있습니다.")
    for frame in frames:
        if not isinstance(frame.snapshot, LogicSnapshot):
            raise TypeError("MEOW 정의는 MEOW 상태를 받아야 합니다.")
        if frame.snapshot.puzzle != puzzle:
            raise ValueError("풀이 결과가 전달된 문제에서 생성되지 않았습니다.")
        if (
            frame.deduction is not None
            and not isinstance(frame.deduction, Deduction)
            or frame.contradiction is not None
            and not isinstance(frame.contradiction, str)
        ):
            raise TypeError("MEOW 추론과 모순 설명이 필요합니다.")
        for decision in (
            *frame.candidates,
            *((frame.assumption,) if frame.assumption is not None else ()),
        ):
            puzzle.validate_cell(decision)


DEFINITION = PuzzleDefinition(
    key="meow",
    title="MEOW · Queens",
    symbols=tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    empty=None,
    default_size=8,
    size_range=(1, 26),
    prompt=VISION_REGION_PROMPT,
    presets=MappingProxyType(
        {name: load_preset(name).region_grid for name in PRESET_NAMES}
    ),
    normalize=normalize,
    parse=parse,
    create=create,
    solve=solve,
    grid=lambda puzzle: puzzle.region_grid,
    editor_view=editor_view,
    frame_view=frame_view,
    describe=describe_frame,
    validate_frames=validate_frames,
)

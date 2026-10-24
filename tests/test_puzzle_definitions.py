import json
from dataclasses import replace

import pytest

from meow.definition import DEFINITION as MEOW
from meow.model import Puzzle as MeowPuzzle
from meow.solve_types import Deduction
from meow.solve_types import Technique as MeowTechnique
from meow.state import CellState, LogicSnapshot
from puzzle_common.presentation import FrameKind, PlaybackFrame, build_frames
from puzzle_common.ui_style import ACCENT, BLACK, ORANGE, RED
from sudoku.definition import DEFINITION as SUDOKU
from sudoku.solve_types import (
    Assignment,
    ContradictionKind,
    ContradictionWitness,
    Elimination,
    Technique,
    TechniqueResult,
)


@pytest.mark.parametrize("definition", (MEOW, SUDOKU))
def test_definition_roundtrip_and_real_native_trace(definition):
    raw = next(iter(definition.presets.values()))
    grid = definition.normalize([list(row) for row in raw])
    assert isinstance(grid, tuple) and all(isinstance(row, tuple) for row in grid)
    payload = {"regions": raw} if definition is MEOW else raw
    assert definition.parse(json.dumps(payload)) == grid
    puzzle = definition.create(grid)
    assert definition.grid(puzzle) == grid
    assert definition.editor_view(grid).size == len(grid)
    result = definition.solve(puzzle)
    frames = build_frames(result)
    definition.validate_frames(puzzle, frames)
    assert definition.frame_view(puzzle, frames[-1]).source is frames[-1].snapshot
    assert definition.describe(frames[-1], result).title


def test_create_keeps_incomplete_and_conflicting_grids_editable_but_rejects_start():
    blank = SUDOKU.normalize([[0] * 9 for _ in range(9)])
    with pytest.raises(ValueError):
        SUDOKU.create(blank)
    conflict = [list(row) for row in blank]
    conflict[0][:2] = [1, 1]
    grid = SUDOKU.normalize(conflict)
    assert SUDOKU.editor_view(grid).cells[0][0].marks[0].color == RED
    with pytest.raises(ValueError):
        SUDOKU.create(grid)
    with pytest.raises(ValueError):
        MEOW.create(MEOW.normalize([[None]]))


def test_sudoku_projection_preserves_givens_removed_candidates_and_highlights():
    grid = [[0] * 9 for _ in range(9)]
    grid[0][0] = 1
    puzzle = SUDOKU.create(SUDOKU.normalize(grid))
    candidates = tuple(tuple(frozenset({2, 3}) for _ in range(9)) for _ in range(9))
    deduction = TechniqueResult(
        Technique.NAKED_PAIR,
        eliminations=(Elimination((0, 1), frozenset({4})),),
        evidence_cells=((0, 2),),
        context_cells=((0, 3),),
    )
    frame = PlaybackFrame(
        FrameKind.DEDUCTION,
        (puzzle.grid, candidates),
        deduction=deduction,
        assumption=Assignment((1, 0), 2),
    )
    view = SUDOKU.frame_view(puzzle, frame)
    assert view.cells[0][0].marks[0].color == BLACK
    assert {(mark.text, mark.slot, mark.struck) for mark in view.cells[0][1].marks} == {
        ("2", 1, False),
        ("3", 2, False),
        ("4", 3, True),
    }
    assert view.cells[0][2].highlights and view.cells[0][3].highlights
    assert view.cells[1][0].outline == ORANGE
    refuted = SUDOKU.frame_view(puzzle, replace(frame, kind=FrameKind.REFUTATION))
    assert refuted.cells[1][0].outline is None
    assert (*RED, 80) in refuted.cells[1][0].highlights


def test_meow_projection_preserves_regions_cat_cross_and_assumption():
    puzzle = MeowPuzzle([["A", "A"], ["B", "B"]])
    snapshot = LogicSnapshot(
        puzzle,
        ((CellState.CAT, CellState.EXCLUDED), (CellState.POSSIBLE, CellState.POSSIBLE)),
    )
    frame = PlaybackFrame(
        FrameKind.DEDUCTION,
        snapshot,
        deduction=Deduction(
            MeowTechnique.ROW_SINGLE, placements=((0, 0),), exclusions=((0, 1),)
        ),
        assumption=(0, 0),
    )
    view = MEOW.frame_view(puzzle, frame)
    assert view.regions == puzzle.region_grid
    assert view.cells[0][0].marks[0].kind == "cat"
    assert view.cells[0][0].marks[0].color == ORANGE
    assert view.cells[0][0].outline == ORANGE
    assert view.cells[0][1].marks[0].kind == "cross"
    assert view.cells[0][1].marks[0].color == RED
    fresh = MEOW.frame_view(puzzle, replace(frame, assumption=None))
    assert fresh.cells[0][0].marks[0].color == ACCENT


def test_definitions_reject_foreign_snapshots_and_foreign_semantics():
    meow = MEOW.create((("A",),))
    sudoku = SUDOKU.create(next(iter(SUDOKU.presets.values())))
    meow_frame = build_frames(MEOW.solve(meow))[0]
    sudoku_frame = build_frames(SUDOKU.solve(sudoku))[0]
    for definition, puzzle, frame in (
        (MEOW, meow, sudoku_frame),
        (SUDOKU, sudoku, meow_frame),
    ):
        with pytest.raises(TypeError):
            definition.validate_frames(puzzle, (frame,))
    with pytest.raises(ValueError):
        MEOW.validate_frames(MeowPuzzle([["B"]]), (meow_frame,))
    with pytest.raises(TypeError):
        SUDOKU.validate_frames(
            sudoku,
            (
                replace(
                    sudoku_frame,
                    deduction=Deduction(MeowTechnique.ROW_SINGLE, placements=((0, 0),)),
                ),
            ),
        )


def test_sudoku_contradiction_keeps_witness_and_unit_highlights():
    puzzle = SUDOKU.create(next(iter(SUDOKU.presets.values())))
    frame = build_frames(SUDOKU.solve(puzzle))[0]
    witness = ContradictionWitness(
        ContradictionKind.MISSING_DIGIT,
        cells=((0, 0),),
        unit_index=0,
        digits=frozenset({2}),
    )
    view = SUDOKU.frame_view(
        puzzle, replace(frame, kind=FrameKind.LOGIC_END, contradiction=witness)
    )
    assert (*RED, 80) in view.cells[0][0].highlights
    assert (*RED, 35) in view.cells[0][8].highlights
    assert not view.cells[1][8].highlights


@pytest.mark.parametrize("bad_value", (True, -1, 10, "1"))
def test_sudoku_validation_rejects_invalid_native_snapshot_values(bad_value):
    puzzle = SUDOKU.create(next(iter(SUDOKU.presets.values())))
    frame = build_frames(SUDOKU.solve(puzzle))[0]
    grid = [list(row) for row in frame.snapshot[0]]
    grid[0][0] = bad_value
    with pytest.raises(TypeError):
        SUDOKU.validate_frames(
            puzzle,
            (
                replace(
                    frame,
                    snapshot=(tuple(tuple(row) for row in grid), frame.snapshot[1]),
                ),
            ),
        )


def test_sudoku_validation_rejects_another_start_grid_and_mutable_candidates():
    puzzle = SUDOKU.create(next(iter(SUDOKU.presets.values())))
    frame = build_frames(SUDOKU.solve(puzzle))[0]
    with pytest.raises(ValueError):
        SUDOKU.validate_frames(
            puzzle,
            (
                replace(
                    frame,
                    snapshot=(tuple((0,) * 9 for _ in range(9)), frame.snapshot[1]),
                ),
            ),
        )
    with pytest.raises(TypeError):
        SUDOKU.validate_frames(
            puzzle,
            (
                replace(
                    frame,
                    snapshot=(
                        frame.snapshot[0],
                        tuple(
                            tuple(set(values) for values in row)
                            for row in frame.snapshot[1]
                        ),
                    ),
                ),
            ),
        )


def test_definition_metadata_matches_native_editor_domains():
    assert (MEOW.symbols, MEOW.empty, MEOW.default_size, MEOW.size_range) == (
        tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
        None,
        8,
        (1, 26),
    )
    assert (SUDOKU.symbols, SUDOKU.empty, SUDOKU.default_size, SUDOKU.size_range) == (
        tuple(range(1, 10)),
        0,
        9,
        (9, 9),
    )

import asyncio
from dataclasses import replace
from unittest.mock import Mock

import pygame
import pytest
from sample_puzzles import UNIQUE_GRID, UNIQUE_SOLUTION

from puzzle_common.engine import SolveResult
from puzzle_common.playback import PlaybackScreen
from puzzle_common.presentation import FrameKind
from puzzle_common.ui_style import ACCENT_YELLOW, ORANGE, RED, wrap_text
from sudoku.board import Grid, Puzzle
from sudoku.definition import DEFINITION, load_puzzle_catalog
from sudoku.solve_types import Assignment, Elimination, Technique, TechniqueResult
from sudoku.solver import solve as solve_sudoku


@pytest.fixture(scope="module")
def solved_case() -> tuple[Grid, SolveResult]:
    puzzle = Puzzle(UNIQUE_GRID)
    return puzzle.grid, solve_sudoku(puzzle)


@pytest.fixture(autouse=True)
def pygame_display() -> None:
    pygame.init()
    yield
    pygame.display.quit()


def test_presentation_keeps_assumption_reason_and_structured_effects() -> None:
    puzzle = Puzzle(load_puzzle_catalog()["극한"])
    visualizer = PlaybackScreen(DEFINITION, puzzle.grid, solve_sudoku(puzzle))
    visualizer.current_step_index = next(
        index
        for index, frame in enumerate(visualizer.frames)
        if frame.deduction is not None
        and Assignment((1, 6), 5) in frame.deduction.assignments
        and frame.active_assumption == Assignment((1, 2), 1)
    )

    details = visualizer._presentation(visualizer.current_frame)

    assert details.title == "논리 기법"
    assert details.reason == "표시된 칸에 가능한 후보가 하나뿐입니다."
    assert details.effects == (("확정 칸 · 1", ("R2C7 = 5",)),)
    assert details.assumption == "R2C3 = 1"
    assert [text for text, _ in details.annotations] == [
        "Naked Single",
        "한 단계 가정 중",
    ]
    visualizer.draw()


def test_multiple_solution_warning_and_last_digit_label() -> None:
    grid = [list(row) for row in UNIQUE_SOLUTION]
    for row, col in ((0, 3), (0, 4), (3, 3), (3, 4)):
        grid[row][col] = 0
    puzzle = Puzzle(grid)
    visualizer = PlaybackScreen(DEFINITION, puzzle.grid, solve_sudoku(puzzle))

    assert "복수해" in visualizer._status_badge()[0]
    visualizer.current_step_index = next(
        index
        for index, step in enumerate(visualizer.frames)
        if step.deduction is not None
        and all(value for row in step.snapshot[0] for value in row)
    )
    details = visualizer._presentation(visualizer.current_frame)
    assert details.annotations[0][0] == "Last Digit"
    visualizer.draw()


@pytest.mark.parametrize("kind", (FrameKind.PROBE_START, FrameKind.DEDUCTION))
def test_multiple_solution_reason_remains_visible_during_assumption(kind) -> None:
    grid = [list(row) for row in UNIQUE_SOLUTION]
    for row, col in ((0, 3), (0, 4), (3, 3), (3, 4)):
        grid[row][col] = 0
    puzzle = Puzzle(grid)
    visualizer = PlaybackScreen(DEFINITION, puzzle.grid, solve_sudoku(puzzle))
    visualizer.current_step_index = next(
        index
        for index, frame in enumerate(visualizer.frames)
        if frame.kind is kind and frame.active_assumption is not None
    )
    details = visualizer._presentation(visualizer.current_frame)
    reason_lines = wrap_text(
        details.reason, visualizer.fonts.body, visualizer.panel_rect.width - 36
    )
    assert len(reason_lines) >= 1
    body = Mock(wraps=visualizer.fonts.body)
    visualizer.fonts = replace(visualizer.fonts, body=body)

    visualizer.draw()

    rendered = [call.args[0] for call in body.render.call_args_list]
    assert all(line in rendered for line in reason_lines)
    assert any(details.assumption in line for line in rendered)
    assert all(
        any(item in line for line in rendered)
        for _, items in details.effects
        for item in items
    )


def test_removed_candidate_has_a_red_strike(
    solved_case: tuple[Grid, SolveResult],
) -> None:
    visualizer = PlaybackScreen(DEFINITION, *solved_case)
    visualizer.screen.fill((255, 255, 255))

    frame = replace(
        visualizer.current_frame,
        deduction=TechniqueResult(
            Technique.NAKED_PAIR,
            eliminations=(Elimination((0, 2), frozenset({5})),),
        ),
    )
    view = DEFINITION.frame_view(solved_case[0], frame)
    mark = next(mark for mark in view.cells[0][2].marks if mark.text == "5")
    assert mark.slot == 4 and mark.struck and mark.color == RED
    visualizer._draw_board(frame)

    center = visualizer.layout.cell_rect((0, 2)).center
    assert tuple(visualizer.screen.get_at((center[0] - 4, center[1]))[:3]) == (
        220,
        38,
        38,
    )


def test_restore_explains_the_failed_attempt_without_orange_highlighting() -> None:
    puzzle = Puzzle(load_puzzle_catalog()["극한"])
    visualizer = PlaybackScreen(DEFINITION, puzzle.grid, solve_sudoku(puzzle))
    frame = next(
        frame for frame in visualizer.frames if frame.kind is FrameKind.RESTORE
    )

    details = visualizer._presentation(frame)
    assert frame.assumption is not None
    assert frame.active_assumption is None
    assert details.title == "원래 상태 복원"
    assert "원래 상태" in details.reason
    assert details.assumption == ""
    assert ("한 단계 가정 중", ORANGE) not in details.annotations

    visualizer._draw_board(frame)
    with_decision = pygame.image.tobytes(visualizer.screen, "RGB")
    visualizer._draw_board(replace(frame, assumption=None))
    assert pygame.image.tobytes(visualizer.screen, "RGB") == with_decision


def test_new_logic_and_selection_stages_have_specific_reasons() -> None:
    puzzle = Puzzle(load_puzzle_catalog()["극한"])
    visualizer = PlaybackScreen(DEFINITION, puzzle.grid, solve_sudoku(puzzle))
    logic_end = next(
        frame for frame in visualizer.frames if frame.kind is FrameKind.LOGIC_END
    )
    selection = next(
        frame for frame in visualizer.frames if frame.kind is FrameKind.PROBING_SELECT
    )

    assert visualizer._presentation(logic_end).title == "논리 정체"
    details = visualizer._presentation(selection)
    assert details.title == "가정 후보 선택"
    assert f"{len(selection.candidates)}개" in details.reason
    assert "H1 점수 순" in details.reason
    empty_reason = visualizer._presentation(replace(selection, candidates=())).reason
    assert "후보가 없" in empty_reason and "탐색" in empty_reason


def test_refutation_keeps_red_fill_but_has_no_active_assumption() -> None:
    puzzle = Puzzle(load_puzzle_catalog()["전문가"])
    visualizer = PlaybackScreen(DEFINITION, puzzle.grid, solve_sudoku(puzzle))
    frame = next(
        frame for frame in visualizer.frames if frame.kind is FrameKind.REFUTATION
    )
    details = visualizer._presentation(frame)

    assert frame.assumption is not None
    assert frame.active_assumption is None
    assert details.title == "귀류 결론"
    assert details.assumption == ""
    assert ("한 단계 가정 중", ORANGE) not in details.annotations
    visualizer._draw_board(frame)

    view = DEFINITION.frame_view(puzzle.grid, frame)
    row, column = frame.assumption.cell
    cell = view.cells[row][column]
    assert cell.highlights == ((*ACCENT_YELLOW, 70), (*RED, 65), (*RED, 80))
    assert cell.outline is None


def test_long_reason_preserves_effects_and_active_assumption(solved_case, monkeypatch):
    puzzle, result = solved_case
    frame = PlaybackScreen(DEFINITION, puzzle, result).current_frame
    details = replace(
        DEFINITION.describe(puzzle, frame, result),
        reason="표시된 칸에 가능한 후보가 하나뿐입니다. " * 100,
        effects=(("후보 제거 · 1", ("R1C3: 5",)),),
        assumption="R1C3 = 1",
    )
    visualizer = PlaybackScreen(DEFINITION, puzzle, result)
    monkeypatch.setattr(visualizer, "_presentation", lambda frame: details)
    body = Mock(wraps=visualizer.fonts.body)
    visualizer.fonts = replace(visualizer.fonts, body=body)

    visualizer.draw()

    rendered = [call.args[0] for call in body.render.call_args_list]
    assert "…" in rendered
    assert "R1C3: 5" in rendered
    assert any(details.assumption in text for text in rendered)


@pytest.mark.parametrize("snapshot", (None, "foreign", ((), ()), ((0,) * 9, (0,) * 9)))
def test_visualizer_rejects_foreign_snapshots_before_configuring_display(
    solved_case: tuple[Grid, SolveResult], snapshot, monkeypatch
) -> None:
    puzzle, result = solved_case
    logic = replace(result.run.initial_logic_result, initial_state=snapshot)
    foreign = replace(result, run=replace(result.run, initial_logic_result=logic))

    def forbidden_display(*args):
        pytest.fail("Invalid native payload reached display configuration")

    monkeypatch.setattr("puzzle_common.playback.configure_display", forbidden_display)
    with pytest.raises(TypeError, match="grid/candidates"):
        PlaybackScreen(DEFINITION, puzzle, foreign)


def test_run_yields_a_frame_then_handles_a_quit_event(
    solved_case: tuple[Grid, SolveResult],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visualizer = PlaybackScreen(DEFINITION, *solved_case)
    draw_calls: list[None] = []
    frame_calls: list[pygame.time.Clock] = []

    monkeypatch.setattr(visualizer, "draw", lambda: draw_calls.append(None))

    async def advance_frame(clock: pygame.time.Clock) -> float:
        frame_calls.append(clock)
        await asyncio.sleep(0)
        return 1 / 60

    monkeypatch.setattr("puzzle_common.playback.next_frame", advance_frame)
    monkeypatch.setattr(
        pygame.event,
        "get",
        lambda: [pygame.event.Event(pygame.QUIT)],
    )

    assert asyncio.run(visualizer.run()) is False
    assert draw_calls == [None]
    assert len(frame_calls) == 1

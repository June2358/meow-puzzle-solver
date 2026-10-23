import pytest

from puzzle_common.engine import LogicStatus, Outcome
from puzzle_common.presentation import FrameKind, build_frames
from sudoku.board import Puzzle
from sudoku.puzzle_catalog import load_puzzle_catalog
from sudoku.solve_types import Technique
from sudoku.solver import SudokuSolver

EXPECTED_DIFFICULTIES = (
    "쉬움",
    "보통",
    "어려움",
    "전문가",
    "마스터",
    "극한",
)


def test_catalog_has_the_six_display_names() -> None:
    catalog = load_puzzle_catalog()

    assert tuple(catalog) == EXPECTED_DIFFICULTIES


@pytest.mark.parametrize(
    ("difficulty", "required_technique", "required_kind"),
    [
        ("쉬움", Technique.NAKED_SINGLE, None),
        ("보통", Technique.LOCKED_PAIR, None),
        ("어려움", Technique.HIDDEN_TRIPLE, None),
        ("전문가", Technique.REFUTATION, FrameKind.REFUTATION),
        ("마스터", Technique.REFUTATION, FrameKind.REFUTATION),
        ("극한", None, FrameKind.SEARCH),
    ],
)
def test_builtin_puzzle_keeps_its_advertised_trace_role(
    difficulty: str,
    required_technique: Technique | None,
    required_kind: FrameKind | None,
) -> None:
    puzzle = Puzzle(load_puzzle_catalog()[difficulty])

    result = SudokuSolver(puzzle).solve()
    assert result.outcome is Outcome.UNIQUE
    assert result.solution is not None

    frames = build_frames(result)
    techniques = {
        step.deduction.technique for step in frames if step.deduction is not None
    }
    kinds = {step.kind for step in frames}

    if required_technique is not None:
        assert required_technique in techniques
    if required_kind is not None:
        assert required_kind in kinds
    if difficulty == "쉬움":
        assert techniques <= {
            Technique.FULL_HOUSE,
            Technique.NAKED_SINGLE,
            Technique.HIDDEN_SINGLE,
        }
    if difficulty in {"쉬움", "보통", "어려움"}:
        assert FrameKind.PROBE_START not in kinds
        assert FrameKind.SEARCH not in kinds
    if difficulty == "전문가":
        assert sum(step.kind is FrameKind.REFUTATION for step in frames) == 1
        assert FrameKind.SEARCH not in kinds
    if difficulty == "마스터":
        assert sum(step.kind is FrameKind.REFUTATION for step in frames) >= 2
        assert FrameKind.SEARCH not in kinds
    if difficulty == "극한":
        assumption_count = sum(step.kind is FrameKind.PROBE_START for step in frames)
        assert assumption_count > 0
        assert assumption_count == sum(
            step.kind is FrameKind.PROBE_END and step.status is LogicStatus.STALLED
            for step in frames
        )
        assert FrameKind.REFUTATION not in kinds
        assert not any(
            step.kind is FrameKind.PROBE_END and step.status is LogicStatus.SOLVED
            for step in frames
        )
        assert any(step.active_assumption is not None for step in frames)

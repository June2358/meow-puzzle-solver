import pytest

from sudoku.board import Puzzle
from sudoku.puzzle_catalog import load_puzzle_catalog
from sudoku.solve_types import SolveStatus, StepKind, Technique
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
        ("전문가", Technique.REFUTATION, StepKind.REFUTATION),
        ("마스터", Technique.REFUTATION, StepKind.REFUTATION),
        ("극한", None, StepKind.SEARCH_FALLBACK),
    ],
)
def test_builtin_puzzle_keeps_its_advertised_trace_role(
    difficulty: str,
    required_technique: Technique | None,
    required_kind: StepKind | None,
) -> None:
    puzzle = Puzzle(load_puzzle_catalog()[difficulty])

    result = SudokuSolver(puzzle).solve()
    assert result.status is SolveStatus.SOLVED_UNIQUE
    assert result.solution is not None

    techniques = {
        step.deduction.technique for step in result.steps if step.deduction is not None
    }
    kinds = {step.kind for step in result.steps}

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
        assert StepKind.ASSUMPTION not in kinds
        assert StepKind.SEARCH_FALLBACK not in kinds
    if difficulty == "전문가":
        assert sum(step.kind is StepKind.REFUTATION for step in result.steps) == 1
        assert StepKind.SEARCH_FALLBACK not in kinds
    if difficulty == "마스터":
        assert sum(step.kind is StepKind.REFUTATION for step in result.steps) >= 2
        assert StepKind.SEARCH_FALLBACK not in kinds
    if difficulty == "극한":
        assumption_count = sum(
            step.kind is StepKind.ASSUMPTION for step in result.steps
        )
        assert assumption_count > 0
        assert assumption_count == sum(
            step.kind is StepKind.ASSUMPTION_STALLED for step in result.steps
        )
        assert StepKind.REFUTATION not in kinds
        assert StepKind.ASSUMPTION_SOLVED not in kinds
        assert max(step.depth for step in result.steps) == 1

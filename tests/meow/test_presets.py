from meow.exact_solver import ExactStatus
from meow.puzzle_catalog import PRESET_NAMES, load_preset
from meow.solver import SolveOutcome, solve


def test_six_presets_have_stable_solver_paths() -> None:
    expected = {
        "쉬움": (4, SolveOutcome.SOLVED_WITH_LOGIC),
        "보통": (7, SolveOutcome.SOLVED_WITH_LOGIC),
        "어려움": (11, SolveOutcome.SOLVED_WITH_LOGIC),
        "전문가": (5, SolveOutcome.SOLVED_WITH_PROBING),
        "마스터": (10, SolveOutcome.SOLVED_WITH_PROBING),
        "극한": (8, SolveOutcome.SOLVED_WITH_PROBING),
    }

    assert tuple(expected) == PRESET_NAMES
    for name, (expected_size, expected_outcome) in expected.items():
        puzzle = load_preset(name)
        result = solve(puzzle)
        assert puzzle.size == expected_size
        assert result.exact_result.status is ExactStatus.UNIQUE
        assert result.outcome is expected_outcome
        assert result.solution is not None

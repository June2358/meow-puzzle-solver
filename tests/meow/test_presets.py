from meow.definition import PRESET_NAMES, load_preset
from meow.solver import solve
from puzzle_common.engine import LogicStatus, Outcome


def test_six_presets_have_stable_solver_paths() -> None:
    expected = {
        "쉬움": (4, LogicStatus.SOLVED),
        "보통": (7, LogicStatus.SOLVED),
        "어려움": (11, LogicStatus.SOLVED),
        "전문가": (5, LogicStatus.STALLED),
        "마스터": (10, LogicStatus.STALLED),
        "극한": (8, LogicStatus.STALLED),
    }

    assert tuple(expected) == PRESET_NAMES
    for name, (expected_size, expected_status) in expected.items():
        puzzle = load_preset(name)
        result = solve(puzzle)
        assert puzzle.size == expected_size
        assert result.outcome is Outcome.UNIQUE
        assert result.run.initial_logic_result.status is expected_status
        assert result.solution is not None

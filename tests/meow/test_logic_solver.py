import pytest

from meow.definition import load_preset
from meow.model import Puzzle
from meow.solver import solve_logically
from meow.state import CellState, LogicSnapshot, LogicState
from puzzle_common.engine import LogicStatus


def _puzzle(*rows: str) -> Puzzle:
    return Puzzle.from_region_grid(tuple(tuple(row) for row in rows))


def test_deterministic_logic_solves_a_known_puzzle() -> None:
    result = solve_logically(load_preset("보통"))

    assert result.status is LogicStatus.SOLVED
    assert result.final_state.cats == frozenset(
        {
            (0, 0),
            (1, 5),
            (2, 3),
            (3, 1),
            (4, 4),
            (5, 2),
            (6, 6),
        }
    )
    assert result.steps


def test_deterministic_logic_stalls_instead_of_guessing() -> None:
    result = solve_logically(_puzzle("ABCD", "ABCD", "ABCD", "ABCD"))

    assert result.status is LogicStatus.STALLED
    assert not result.final_state.cats


def test_deterministic_logic_reports_a_contradiction() -> None:
    result = solve_logically(_puzzle("AB", "AB"))

    assert result.status is LogicStatus.CONTRADICTION
    assert result.final_state.has_contradiction()
    assert result.contradiction


@pytest.mark.parametrize(
    ("rows", "cats", "excluded", "message"),
    (
        (
            ("ABC",) * 3,
            {(0, 0), (0, 2)},
            {(1, 0), (1, 1), (1, 2)},
            "R1C1과 R1C3의 고양이가 충돌합니다.",
        ),
        (
            ("ABC",) * 3,
            set(),
            {(0, 0), (0, 1), (0, 2), (1, 0), (2, 0)},
            "행 1에 가능한 칸이 없습니다.",
        ),
        (("ABC",) * 3, set(), {(0, 0), (1, 0), (2, 0)}, "열 1에 가능한 칸이 없습니다."),
        (
            ("AAB", "ACC", "BCC"),
            set(),
            {(0, 0), (0, 1), (1, 0)},
            "표시된 색상 영역에 고양이를 놓을 칸이 없습니다.",
        ),
        (("ABC",) * 3, set(), set(), None),
    ),
)
def test_snapshot_and_logic_use_the_same_first_contradiction(
    rows, cats, excluded, message
) -> None:
    puzzle = _puzzle(*rows)
    snapshot = LogicSnapshot(
        puzzle,
        tuple(
            tuple(
                CellState.CAT
                if (row, col) in cats
                else CellState.EXCLUDED
                if (row, col) in excluded
                else CellState.POSSIBLE
                for col in range(puzzle.size)
            )
            for row in range(puzzle.size)
        ),
    )

    assert snapshot.contradiction_message() == message
    assert snapshot.has_contradiction() is (message is not None)
    if message is not None:
        result = solve_logically(puzzle, LogicState.from_snapshot(snapshot))
        assert result.status is LogicStatus.CONTRADICTION
        assert result.contradiction == message
        assert result.steps == ()

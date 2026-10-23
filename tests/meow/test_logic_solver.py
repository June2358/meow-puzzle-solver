from meow.logic_solver import solve_logically
from meow.model import Puzzle
from meow.puzzle_catalog import load_preset
from meow.solve_types import LogicStatus


def _puzzle(*rows: str) -> Puzzle:
    return Puzzle.from_region_grid(tuple(tuple(row) for row in rows))


def test_deterministic_logic_solves_a_known_puzzle() -> None:
    result = solve_logically(load_preset("보통"))

    assert result.status is LogicStatus.SOLVED_LOGICALLY
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
    assert result.message

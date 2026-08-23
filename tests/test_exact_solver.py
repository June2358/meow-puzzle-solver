from meow.exact_solver import ExactStatus, verify_exact
from meow.model import Puzzle
from meow.puzzle_catalog import load_preset


def _puzzle(*rows: str) -> Puzzle:
    return Puzzle.from_region_grid(tuple(tuple(row) for row in rows))


def test_exact_solver_classifies_unique_multiple_and_unsolvable() -> None:
    unique = verify_exact(load_preset("보통"))
    multiple = verify_exact(_puzzle("ABCD", "ABCD", "ABCD", "ABCD"))
    unsolvable = verify_exact(_puzzle("AB", "AB"))

    assert unique.status is ExactStatus.UNIQUE
    assert unique.solutions == (
        (
            (0, 0),
            (1, 5),
            (2, 3),
            (3, 1),
            (4, 4),
            (5, 2),
            (6, 6),
        ),
    )
    assert multiple.status is ExactStatus.MULTIPLE
    assert len(multiple.solutions) == 2
    assert unsolvable.status is ExactStatus.UNSOLVABLE
    assert unsolvable.solutions == ()

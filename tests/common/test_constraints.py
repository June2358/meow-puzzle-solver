import pytest

from puzzle_common.constraints import locked_candidate_targets


@pytest.mark.parametrize(
    ("evidence", "possible", "expected"),
    [
        ((1, 2), {1, 2, 3, 4}, (0, (4, 3))),
        ((1, 2), {1, 2}, None),
        ((1, 5), {1, 2, 3, 4, 5}, None),
        ((), {1, 2, 3, 4}, None),
    ],
)
def test_lock_requires_one_target_and_keeps_its_cell_order(
    evidence, possible, expected
) -> None:
    assert (
        locked_candidate_targets(
            frozenset({1, 2}),
            evidence,
            ((2, 4, 1, 3), (5, 6)),
            lambda cell: int(cell >= 5),
            possible.__contains__,
        )
        == expected
    )

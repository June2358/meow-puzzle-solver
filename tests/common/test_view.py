import pytest

from puzzle_common.view import BoardView, CellMark, CellView


@pytest.mark.parametrize(
    ("cells", "regions"),
    [((), ()), (((CellView(),),), ()), (((CellView(), CellView()),), ((0,),))],
)
def test_board_rejects_incompatible_geometry(cells, regions):
    with pytest.raises(ValueError):
        BoardView(object(), cells, regions)


@pytest.mark.parametrize("slot", [-1, 9, True])
def test_marks_reject_invalid_candidate_positions(slot):
    with pytest.raises(ValueError):
        CellMark(text="1", slot=slot)

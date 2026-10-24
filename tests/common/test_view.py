import pytest

from puzzle_common.view import BoardView, CellMark, CellView


def test_board_keeps_source_and_native_region_labels():
    source = object()
    mark = CellMark(text="3", slot=2, struck=True)
    view = BoardView(source, ((CellView(marks=(mark,)),),), (("A",),))
    assert view.source is source
    assert view.size == 1
    assert view.cells[0][0].marks == (mark,)
    assert view.regions == (("A",),)


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

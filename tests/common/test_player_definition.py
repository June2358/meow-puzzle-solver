from types import SimpleNamespace

import pygame
import pytest

from puzzle_common.engine import LogicRun, LogicStatus, Outcome, SolveResult, SolveRun
from puzzle_common.playback import PlaybackScreen
from puzzle_common.view import BoardView, CellMark, CellView, PlaybackDetails


@pytest.fixture
def player_case():
    pygame.init()
    grid = ((1,),)
    snapshot = object()
    result = SolveResult(
        Outcome.UNIQUE,
        SolveRun(
            LogicRun(LogicStatus.SOLVED, snapshot, snapshot, ()), (), (snapshot,), False
        ),
    )
    validated = []
    definition = SimpleNamespace(
        title="테스트 퍼즐",
        validate_frames=lambda source, frames: validated.append((source, frames)),
        frame_view=lambda source, frame: BoardView(
            frame.snapshot, ((CellView(marks=(CellMark(text="1"),)),),), ((0,),)
        ),
        describe=lambda source, frame, result: PlaybackDetails("완료", "유일한 해"),
    )
    yield definition, grid, result, validated
    pygame.quit()


def test_player_rejects_display_data_from_another_puzzle(player_case):
    definition, grid, result, _ = player_case
    definition.frame_view = lambda source, frame: BoardView(
        object(), ((CellView(),),), ((0,),)
    )
    player = PlaybackScreen(definition, grid, result)
    with pytest.raises(ValueError, match="문제"):
        player.draw()

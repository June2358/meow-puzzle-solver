from types import SimpleNamespace

import pygame
import pytest

from puzzle_common.engine import LogicRun, LogicStatus, Outcome, SolveResult, SolveRun
from puzzle_common.playback import PlaybackScreen
from puzzle_common.view import BoardView, CellMark, CellView, PlaybackDetails


@pytest.fixture
def player_case():
    pygame.init()
    puzzle = object()
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
        grid=lambda _: ((1,),),
        validate_frames=lambda source, frames: validated.append((source, frames)),
        frame_view=lambda source, frame: BoardView(
            frame.snapshot, ((CellView(marks=(CellMark(text="1"),)),),), ((0,),)
        ),
        describe=lambda frame, result: PlaybackDetails("완료", "유일한 해"),
    )
    yield definition, puzzle, result, validated
    pygame.quit()


def test_one_player_uses_definition_data_and_keeps_the_certified_result(player_case):
    definition, puzzle, result, validated = player_case
    player = PlaybackScreen(definition, puzzle, result)
    player.draw()
    assert type(player) is PlaybackScreen
    assert player.result is result
    assert validated == [(puzzle, player.frames)]
    assert player._presentation(player.current_frame).title == "완료"


def test_player_rejects_display_data_from_another_puzzle(player_case):
    definition, puzzle, result, _ = player_case
    definition.frame_view = lambda source, frame: BoardView(
        object(), ((CellView(),),), ((0,),)
    )
    player = PlaybackScreen(definition, puzzle, result)
    with pytest.raises(ValueError, match="문제"):
        player.draw()

"""Puzzle definitions supply semantics and data, never screen implementations."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal

from .board import editor_view, frame_view
from .engine import SolveResult
from .presentation import FrameKind, PlaybackFrame, describe_frame
from .view import BoardView, Cell, FrameData, Grid, PlaybackDetails


@dataclass(frozen=True, slots=True)
class PuzzleDefinition:
    key: str
    title: str
    symbols: tuple[int | str, ...]
    empty: int | None
    default_size: int
    size_range: tuple[int, int]
    prompt: str
    presets: Mapping[str, Grid]
    normalize: Callable[[object], Grid]
    parse: Callable[[str], Grid]
    solve: Callable[[Grid], SolveResult]
    frame_data: Callable[[Grid, PlaybackFrame], FrameData]
    validate_frame: Callable[[Grid, PlaybackFrame], None]
    regions: Grid | None = None
    value_mark: Literal["text", "cat"] = "text"
    value_label: str = ""
    conflicts: Callable[[Grid], frozenset[Cell]] | None = None
    probe_description: str = ""

    def validate_frames(self, grid: Grid, frames: tuple[PlaybackFrame, ...]) -> None:
        grid = self.normalize(grid)
        if not frames:
            raise ValueError("풀이 기록이 비어 있습니다.")
        for frame in frames:
            self.validate_frame(grid, frame)
        if frames[0].kind is not FrameKind.START:
            raise ValueError("풀이 기록은 초기 상태에서 시작해야 합니다.")

    def editor_view(self, grid: Grid) -> BoardView:
        return editor_view(self, self.normalize(grid))

    def frame_view(self, grid: Grid, frame: PlaybackFrame) -> BoardView:
        return frame_view(self, grid, frame, self.frame_data(grid, frame))

    def describe(
        self, grid: Grid, frame: PlaybackFrame, result: SolveResult
    ) -> PlaybackDetails:
        return describe_frame(self, grid, frame, result, self.frame_data(grid, frame))

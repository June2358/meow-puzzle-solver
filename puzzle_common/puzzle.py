"""Puzzle definitions supply semantics and data, never screen implementations."""

from collections.abc import Callable, Mapping
from dataclasses import dataclass

from .engine import SolveResult
from .presentation import PlaybackFrame
from .view import BoardView, Grid, PlaybackDetails


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
    create: Callable[[Grid], object]
    solve: Callable[[object], SolveResult]
    grid: Callable[[object], Grid]
    editor_view: Callable[[Grid], BoardView]
    frame_view: Callable[[object, PlaybackFrame], BoardView]
    describe: Callable[[PlaybackFrame, SolveResult], PlaybackDetails]
    validate_frames: Callable[[object, tuple[PlaybackFrame, ...]], None]

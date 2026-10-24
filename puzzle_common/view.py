"""Immutable display data shared by the editor and playback renderer."""

from dataclasses import dataclass
from typing import Literal

from .ui_style import PRIMARY_DARK, WHITE, Color

type Cell = tuple[int, int]
type Grid = tuple[tuple[int | str | None, ...], ...]
type EffectGroups = tuple[tuple[str, tuple[str, ...]], ...]


@dataclass(frozen=True, slots=True)
class CellMark:
    kind: Literal["text", "cat", "cross"] = "text"
    text: str = ""
    color: Color = PRIMARY_DARK
    slot: int | None = None
    struck: bool = False

    def __post_init__(self) -> None:
        if self.kind not in ("text", "cat", "cross"):
            raise ValueError("지원하지 않는 보드 기호입니다.")
        if self.slot is not None and (
            type(self.slot) is not int or not 0 <= self.slot < 9
        ):
            raise ValueError("후보 위치는 0~8 정수여야 합니다.")


@dataclass(frozen=True, slots=True)
class CellView:
    background: Color = WHITE
    marks: tuple[CellMark, ...] = ()
    highlights: tuple[tuple[int, int, int, int], ...] = ()
    outline: Color | None = None


@dataclass(frozen=True, slots=True)
class BoardView:
    source: object
    cells: tuple[tuple[CellView, ...], ...]
    regions: tuple[tuple[object, ...], ...]

    def __post_init__(self) -> None:
        size = len(self.cells)
        if (
            not 1 <= size <= 26
            or any(len(row) != size for row in self.cells)
            or len(self.regions) != size
            or any(len(row) != size for row in self.regions)
        ):
            raise ValueError("보드와 영역은 같은 크기의 1~26 정사각형이어야 합니다.")
        if any(not isinstance(cell, CellView) for row in self.cells for cell in row):
            raise TypeError("보드는 CellView로 구성되어야 합니다.")

    @property
    def size(self) -> int:
        return len(self.cells)


@dataclass(frozen=True, slots=True)
class PlaybackDetails:
    title: str
    reason: str
    effects: EffectGroups = ()
    annotations: tuple[tuple[str, Color], ...] = ()
    assumption: str = ""
    region_colors: tuple[Color, ...] = ()

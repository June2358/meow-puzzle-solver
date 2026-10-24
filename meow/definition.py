"""MEOW rules and native trace data for the common app."""

from types import MappingProxyType

from puzzle_common.catalog import PuzzleDataError, load_catalog
from puzzle_common.engine import LogicStatus
from puzzle_common.json_input import decode_json
from puzzle_common.presentation import FrameKind, PlaybackFrame
from puzzle_common.puzzle import PuzzleDefinition
from puzzle_common.view import FrameData, Grid

from .model import InvalidRegionMapError, Puzzle, create_puzzle, normalize_draft
from .solve_types import SOLVER_ALGORITHM_LABELS, TECHNIQUE_LABELS, Deduction, UnitKind
from .solver import solve as solve_native
from .state import CellState, LogicSnapshot

PRESET_NAMES = ("쉬움", "보통", "어려움", "전문가", "마스터", "극한")


VISION_REGION_PROMPT = """첨부 이미지의 색상 영역 Queens (1-star Star Battle) 퍼즐을 전사하세요.

규칙:
1. 정사각형 보드에서 N을 판별하고, 각 행이 N칸인 정확히 N개 행을 반환하세요.
2. 각 칸의 색상이나 경계로 구분되는 영역만 식별하세요.
3. 같은 영역의 모든 칸에 동일한 문자열 이름을 사용하세요.
4. 위에서 아래로, 각 행은 왼쪽에서 오른쪽으로 읽으며 처음 만나는 영역부터
   A, B, C, ...로 이름을 붙이세요. 최대 지원 크기는 26×26입니다.
5. 고양이, 퀸, 왕관, X 표시, 힌트, 강조, 점수, 버튼, 텍스트 등 보드 위나
   바깥에 겹친 UI 요소는 무시하세요.
6. 퍼즐을 풀거나 고양이 위치를 추론하거나 영역 경계를 바꾸지 마세요.
7. 설명이나 Markdown 코드 블록 없이 JSON만 반환하세요.
8. "regions" 필드 하나만 포함한 객체를 반환하세요. size, name, source,
   solution, cats, excluded 등 다른 필드는 추가하지 마세요.

필수 형식 예시 (이미지와 일치할 때만 값을 그대로 사용하세요):
{"regions":[["A","A","B"],["C","B","B"],["C","C","B"]]}"""


class PuzzleParseError(InvalidRegionMapError):
    """Raised when input cannot be interpreted as a puzzle document."""


def parse_puzzle_json(text: str) -> Puzzle:
    """Parse the canonical JSON puzzle object.

    The object has exactly one ``regions`` field containing a two-dimensional
    array of region-label strings. No metadata or solution fields are accepted.
    """

    document = decode_json(text, PuzzleParseError)

    if not isinstance(document, dict):
        raise PuzzleParseError("JSON 최상위 값은 객체여야 합니다.")

    unknown_fields = document.keys() - {"regions"}
    if unknown_fields:
        fields = ", ".join(sorted(repr(field) for field in unknown_fields))
        raise PuzzleParseError(f"지원하지 않는 JSON 필드입니다: {fields}")
    if "regions" not in document:
        raise PuzzleParseError("JSON 객체에는 'regions' 필드가 필요합니다.")

    regions = document["regions"]
    if not isinstance(regions, list):
        raise PuzzleParseError("JSON의 'regions'는 행 배열이어야 합니다.")
    if any(not isinstance(row, list) for row in regions):
        raise PuzzleParseError("JSON의 'regions' 각 행은 배열이어야 합니다.")

    try:
        return Puzzle.from_region_grid(regions)
    except InvalidRegionMapError as error:
        # JSON syntax/schema/model failures share one public parse-error type,
        # while preserving the precise validation message (including RnCn).
        raise PuzzleParseError(str(error)) from error


def _validate_preset(grid: object) -> Grid:
    return Puzzle.from_region_grid(grid).region_grid


def load_puzzle_catalog():
    presets = load_catalog(__package__, _validate_preset)
    if set(presets) != set(PRESET_NAMES):
        expected = ", ".join(PRESET_NAMES)
        raise PuzzleDataError(
            f"퍼즐 데이터에는 다음 여섯 프리셋이 필요합니다: {expected}"
        )
    return presets


def load_preset(name: str) -> Puzzle:
    if not isinstance(name, str):
        raise TypeError("프리셋 이름은 문자열이어야 합니다.")
    try:
        grid = load_puzzle_catalog()[name]
    except KeyError as error:
        choices = ", ".join(PRESET_NAMES)
        raise ValueError(
            f"알 수 없는 프리셋 {name!r}입니다. 사용 가능: {choices}"
        ) from error
    return Puzzle.from_region_grid(grid)


def parse(text: str) -> Grid:
    return parse_puzzle_json(text).region_grid


def solve(grid: Grid):
    return solve_native(create_puzzle(grid))


def frame_data(grid: Grid, frame: PlaybackFrame) -> FrameData:
    snapshot = frame.snapshot
    puzzle = snapshot.puzzle
    deduction = frame.deduction
    if deduction is not None:
        region_indices = tuple(
            dict.fromkeys(
                ref.index
                for ref in deduction.evidence_units
                if ref.kind is UnitKind.REGION
            )
        )
    elif frame.kind in (FrameKind.LOGIC_END, FrameKind.PROBE_END) and (
        frame.status is LogicStatus.CONTRADICTION
    ):
        region_indices = tuple(
            index
            for index, region in enumerate(puzzle.regions)
            if not snapshot.cats_in(region) and not snapshot.candidates_for(region)
        )
    else:
        region_indices = ()
    return FrameData(
        source=snapshot,
        values=tuple(
            tuple(int(status is CellState.CAT) for status in row)
            for row in snapshot.status_grid
        ),
        excluded=frozenset(cell for cell in puzzle.cells if snapshot.is_excluded(cell)),
        placements=tuple((cell, None) for cell in deduction.placements)
        if deduction
        else (),
        eliminations=tuple((cell, ()) for cell in deduction.exclusions)
        if deduction
        else (),
        evidence=deduction.evidence_cells if deduction else (),
        decision=(frame.assumption, None) if frame.assumption is not None else None,
        technique=SOLVER_ALGORITHM_LABELS[deduction.algorithm] if deduction else "",
        reason=(
            deduction.explanation
            or f"{TECHNIQUE_LABELS[deduction.technique]}을 적용했습니다."
        )
        if deduction
        else "",
        contradiction=frame.contradiction or "",
        region_labels=tuple(puzzle.region_labels[index] for index in region_indices),
    )


def validate_frame(grid: Grid, frame: PlaybackFrame) -> None:
    if not isinstance(frame.snapshot, LogicSnapshot):
        raise TypeError("MEOW 정의는 MEOW 상태를 받아야 합니다.")
    if frame.snapshot.puzzle.region_grid != grid:
        raise ValueError("풀이 결과가 전달된 문제에서 생성되지 않았습니다.")
    if (
        frame.deduction is not None
        and not isinstance(frame.deduction, Deduction)
        or frame.contradiction is not None
        and not isinstance(frame.contradiction, str)
    ):
        raise TypeError("MEOW 추론과 모순 설명이 필요합니다.")
    for decision in (
        *frame.candidates,
        *((frame.assumption,) if frame.assumption is not None else ()),
    ):
        frame.snapshot.puzzle.validate_cell(decision)


DEFINITION = PuzzleDefinition(
    key="meow",
    title="MEOW · Queens",
    symbols=tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
    empty=None,
    default_size=8,
    size_range=(1, 26),
    prompt=VISION_REGION_PROMPT,
    presets=MappingProxyType(
        {name: load_puzzle_catalog()[name] for name in PRESET_NAMES}
    ),
    normalize=normalize_draft,
    parse=parse,
    solve=solve,
    frame_data=frame_data,
    validate_frame=validate_frame,
    regions=None,
    value_mark="cat",
    value_label="고양이",
    probe_description=(
        "가정 직후 다른 미완성 단위에서 새 고양이가 즉시 확정되는 후보를 "
        "새 고양이 수, 새 2후보 단위 수, 좌표 순으로 선택합니다."
    ),
)

"""논리 풀이와 독립적으로 퍼즐의 해 개수를 검증한다."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from puzzle_common.constraints import has_distinct_representatives

from .model import Cell, Puzzle


class ExactStatus(StrEnum):
    """전수 탐색으로 확인한 퍼즐의 해 상태."""

    UNSOLVABLE = "UNSOLVABLE"
    UNIQUE = "UNIQUE"
    MULTIPLE = "MULTIPLE"


Solution = tuple[Cell, ...]


@dataclass(frozen=True, slots=True)
class ExactResult:
    """최대 두 개까지만 보존한 exact 검증 결과."""

    status: ExactStatus
    solutions: tuple[Solution, ...]


class ExactVerifier:
    """MRV 분기 탐색으로 0해, 유일해, 복수해를 구분한다.

    다른 풀이 규칙이나 그 결과를 입력으로 받지 않는다. 행·열·영역 중 남은
    후보가 가장 적은 단위에서 한 칸을 선택하고 인접 제약을 직접 검사한다.
    두 번째 해를 찾는 즉시 탐색을 종료한다.
    """

    _SOLUTION_LIMIT = 2

    def __init__(self, puzzle: Puzzle) -> None:
        self.puzzle = puzzle
        self._solutions: list[Solution] = []
        self._placements = [-1] * puzzle.size
        self._all_units_mask = (1 << (3 * puzzle.size)) - 1
        self._all_cells_mask = (1 << (puzzle.size * puzzle.size)) - 1
        self._unit_masks = tuple(
            sum(1 << (row * puzzle.size + column) for row, column in unit)
            for unit in puzzle.units
        )
        self._cell_units = tuple(
            (1 << row)
            | (1 << (puzzle.size + column))
            | (1 << (2 * puzzle.size + puzzle.region_of((row, column))))
            for row, column in puzzle.cells
        )
        # Build attacks from the rules independently of the logic engine's conflicts.
        self._conflict_masks = tuple(
            self._unit_masks[row]
            | self._unit_masks[puzzle.size + column]
            | self._unit_masks[2 * puzzle.size + puzzle.region_of((row, column))]
            | sum(
                1 << (adjacent_row * puzzle.size + adjacent_column)
                for adjacent_row in range(max(0, row - 1), min(puzzle.size, row + 2))
                for adjacent_column in range(
                    max(0, column - 1), min(puzzle.size, column + 2)
                )
            )
            for row, column in puzzle.cells
        )

    def verify(self) -> ExactResult:
        """퍼즐을 검증하고, 발견한 해를 최대 두 개까지 반환한다."""

        self._solutions = []
        self._placements = [-1] * self.puzzle.size
        self._search(self._all_units_mask, self._all_cells_mask)

        if not self._solutions:
            status = ExactStatus.UNSOLVABLE
        elif len(self._solutions) == 1:
            status = ExactStatus.UNIQUE
        else:
            status = ExactStatus.MULTIPLE

        return ExactResult(status=status, solutions=tuple(self._solutions))

    def _search(
        self,
        uncovered_units: int,
        candidates: int,
    ) -> None:
        if len(self._solutions) >= self._SOLUTION_LIMIT:
            return
        if uncovered_units == 0:
            solution = tuple(enumerate(self._placements))
            self._solutions.append(solution)
            return

        best_candidates = 0
        best_count = self.puzzle.size * self.puzzle.size + 1
        remaining_units = uncovered_units
        while remaining_units:
            unit_bit = remaining_units & -remaining_units
            unit_candidates = self._unit_masks[unit_bit.bit_length() - 1] & candidates
            candidate_count = unit_candidates.bit_count()
            if candidate_count == 0:
                return
            if candidate_count < best_count:
                best_candidates = unit_candidates
                best_count = candidate_count
            remaining_units ^= unit_bit

        size = self.puzzle.size
        region_candidates = tuple(
            self._unit_masks[index] & candidates
            for index in range(2 * size, 3 * size)
            if uncovered_units & (1 << index)
        )
        for lines in (self._unit_masks[:size], self._unit_masks[size : 2 * size]):
            domains = tuple(
                sum(1 << index for index, line in enumerate(lines) if region & line)
                for region in region_candidates
            )
            if not has_distinct_representatives(domains):
                return

        remaining_candidates = best_candidates
        while remaining_candidates:
            cell_bit = remaining_candidates & -remaining_candidates
            cell_index = cell_bit.bit_length() - 1
            row, column = divmod(cell_index, self.puzzle.size)
            self._placements[row] = column

            self._search(
                uncovered_units & ~self._cell_units[cell_index],
                candidates & ~self._conflict_masks[cell_index],
            )
            self._placements[row] = -1

            if len(self._solutions) >= self._SOLUTION_LIMIT:
                break
            remaining_candidates ^= cell_bit


def verify_exact(puzzle: Puzzle) -> ExactResult:
    """독립 exact 검증을 수행하는 간단한 공개 진입점."""

    return ExactVerifier(puzzle).verify()

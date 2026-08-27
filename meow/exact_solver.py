"""논리 풀이와 독립적으로 퍼즐의 해 개수를 검증한다."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

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

    다른 풀이 규칙이나 그 결과를 입력으로 받지 않는다. 각 행에서 한 칸을
    선택하면서 열, 영역, 인접 제약만 직접 검사하며, 두 번째 해를 찾는 즉시
    탐색을 종료한다.
    """

    _SOLUTION_LIMIT = 2

    def __init__(self, puzzle: Puzzle) -> None:
        self.puzzle = puzzle
        self._solutions: list[Solution] = []
        self._placements = [-1] * puzzle.size
        self._all_rows_mask = (1 << puzzle.size) - 1
        self._all_columns_mask = (1 << puzzle.size) - 1
        self._region_bits = tuple(
            tuple(1 << puzzle.region_of((row, column)) for column in range(puzzle.size))
            for row in range(puzzle.size)
        )
        self._adjacent_column_masks = tuple(
            sum(
                1 << adjacent
                for adjacent in range(max(0, column - 1), min(puzzle.size, column + 2))
            )
            for column in range(puzzle.size)
        )

    def verify(self) -> ExactResult:
        """퍼즐을 검증하고, 발견한 해를 최대 두 개까지 반환한다."""

        self._solutions = []
        self._placements = [-1] * self.puzzle.size
        self._search(
            unassigned_rows=self._all_rows_mask,
            used_columns=0,
            used_regions=0,
        )

        if not self._solutions:
            status = ExactStatus.UNSOLVABLE
        elif len(self._solutions) == 1:
            status = ExactStatus.UNIQUE
        else:
            status = ExactStatus.MULTIPLE

        return ExactResult(status=status, solutions=tuple(self._solutions))

    def _search(
        self,
        unassigned_rows: int,
        used_columns: int,
        used_regions: int,
    ) -> None:
        if len(self._solutions) >= self._SOLUTION_LIMIT:
            return
        if unassigned_rows == 0:
            solution = tuple(enumerate(self._placements))
            self._solutions.append(solution)
            return

        best_row = -1
        best_candidates = 0
        best_count = self.puzzle.size + 1
        remaining_rows = unassigned_rows
        while remaining_rows:
            row_bit = remaining_rows & -remaining_rows
            row = row_bit.bit_length() - 1
            candidates = self._candidate_columns(row, used_columns, used_regions)
            candidate_count = candidates.bit_count()
            if candidate_count == 0:
                return
            if candidate_count < best_count:
                best_row = row
                best_candidates = candidates
                best_count = candidate_count
                if candidate_count == 1:
                    break
            remaining_rows ^= row_bit

        next_unassigned_rows = unassigned_rows & ~(1 << best_row)
        remaining_candidates = best_candidates
        while remaining_candidates:
            column_bit = remaining_candidates & -remaining_candidates
            column = column_bit.bit_length() - 1
            region_bit = self._region_bits[best_row][column]
            self._placements[best_row] = column

            self._search(
                next_unassigned_rows,
                used_columns | column_bit,
                used_regions | region_bit,
            )

            if len(self._solutions) >= self._SOLUTION_LIMIT:
                break
            remaining_candidates ^= column_bit
        self._placements[best_row] = -1

    def _candidate_columns(
        self,
        row: int,
        used_columns: int,
        used_regions: int,
    ) -> int:
        """Return a bitmask of currently legal columns for one row."""

        candidates = self._all_columns_mask & ~used_columns
        # With exactly one cat per row, only the two neighboring rows can be
        # king-adjacent to a candidate in this row.
        if row > 0:
            previous_column = self._placements[row - 1]
            if previous_column >= 0:
                candidates &= ~self._adjacent_column_masks[previous_column]
        if row + 1 < self.puzzle.size:
            next_column = self._placements[row + 1]
            if next_column >= 0:
                candidates &= ~self._adjacent_column_masks[next_column]

        legal_columns = 0
        remaining_columns = candidates
        while remaining_columns:
            column_bit = remaining_columns & -remaining_columns
            column = column_bit.bit_length() - 1
            if not used_regions & self._region_bits[row][column]:
                legal_columns |= column_bit
            remaining_columns ^= column_bit
        return legal_columns


def verify_exact(puzzle: Puzzle) -> ExactResult:
    """독립 exact 검증을 수행하는 간단한 공개 진입점."""

    return ExactVerifier(puzzle).verify()

"""Adapt the shared solving lifecycle to Sudoku's public explanation trace."""

from puzzle_common.engine import Engine, LogicRun, LogicStatus

from .board import Puzzle
from .engine_adapter import SudokuDomain, SudokuSnapshot
from .solve_types import (
    Assignment,
    ContradictionKind,
    ContradictionWitness,
    SolveResult,
    SolveStatus,
    SolveStep,
    StepKind,
    TechniqueResult,
)
from .solver_state import SolverState
from .topology import COLS, ROWS


class SudokuSolver:
    """Explain logic and bivalue one-ply refutations, then find up to two solutions."""

    __slots__ = ("_puzzle",)

    def __init__(self, puzzle: Puzzle):
        if not isinstance(puzzle, Puzzle):
            raise TypeError("SudokuSolver는 Puzzle을 받아야 합니다.")
        self._puzzle = puzzle

    def solve(self) -> SolveResult:
        """Solve with shared propagation, probing, and uniqueness search."""

        state = SolverState(self._puzzle)
        run = Engine(SudokuDomain()).solve(state, solution_limit=2)
        steps = [
            self._step(
                StepKind.INITIAL_STATE,
                run.initial_logic_result.initial_state,
                message="초기 후보 상태",
            )
        ]
        steps.extend(self._logic_steps(run.initial_logic_result))
        for round_ in run.probing_rounds:
            for probe in round_.probes:
                decision = probe.assumption
                row, col = decision.cell
                value = decision.value
                logic = probe.logic_result
                steps.append(
                    self._step(
                        StepKind.ASSUMPTION,
                        logic.initial_state,
                        assumption=decision,
                        message=(
                            f"2후보 셀 가정: R{row + 1}C{col + 1} = {value}로 두고 "
                            "추가 가정 없이 기존 논리만 적용합니다."
                        ),
                    )
                )
                steps.extend(self._logic_steps(logic, assumption=decision))
                if logic.status is LogicStatus.SOLVED:
                    steps.append(
                        self._step(
                            StepKind.ASSUMPTION_SOLVED,
                            logic.final_state,
                            assumption=decision,
                            message=(
                                f"R{row + 1}C{col + 1} = {value} 가정에서 "
                                "추가 가정 없이 해 하나를 완성했습니다."
                            ),
                        )
                    )
                elif logic.status is LogicStatus.STALLED:
                    steps.append(
                        self._step(
                            StepKind.ASSUMPTION_STALLED,
                            logic.final_state,
                            assumption=decision,
                            message=(
                                f"R{row + 1}C{col + 1} = {value} 가정에서는 "
                                "모순도 완성도 나오지 않아 원래 상태로 돌아갑니다."
                            ),
                        )
                    )
            if round_.elimination is not None:
                steps.extend(
                    self._logic_steps(
                        round_.elimination,
                        refuted_assumption=round_.probes[-1].assumption,
                    )
                )

        if run.used_backtrack_search:
            steps.append(
                self._step(
                    StepKind.SEARCH_FALLBACK,
                    state.snapshot(),
                    message=(
                        "2후보 셀이 없거나 모든 2후보 가정이 정체되어, "
                        "여기부터는 MRV 백트래킹으로 전환합니다."
                    ),
                )
            )
        if not run.solutions:
            status = SolveStatus.UNSOLVABLE
            steps.append(
                self._step(
                    StepKind.UNSOLVABLE,
                    state.snapshot(),
                    message="현재 단서로 가능한 해가 없습니다.",
                )
            )
        else:
            status = (
                SolveStatus.SOLVED_MULTIPLE
                if len(run.solutions) >= 2
                else SolveStatus.SOLVED_UNIQUE
            )
            steps.append(
                self._step(
                    StepKind.SOLVED,
                    run.solutions[0],
                    message=(
                        "해가 둘 이상 존재합니다. 표시한 보드는 가능한 해 중 하나입니다."
                        if status is SolveStatus.SOLVED_MULTIPLE
                        else "유일한 해를 확인했습니다."
                    ),
                )
            )
        return SolveResult(status=status, steps=tuple(steps))

    @classmethod
    def _logic_steps(
        cls,
        run: LogicRun,
        *,
        assumption: Assignment | None = None,
        refuted_assumption: Assignment | None = None,
    ) -> list[SolveStep]:
        steps = [
            cls._step(
                StepKind.REFUTATION
                if index == 0 and refuted_assumption is not None
                else StepKind.TECHNIQUE,
                step.after,
                deduction=step.deduction,
                assumption=refuted_assumption
                if index == 0 and refuted_assumption is not None
                else assumption,
            )
            for index, step in enumerate(run.steps)
        ]
        if run.contradiction is not None:
            steps.append(
                cls._step(
                    StepKind.CONTRADICTION,
                    run.final_state,
                    assumption=assumption,
                    contradiction=run.contradiction,
                    message=cls._contradiction_message(run.contradiction),
                )
            )
        return steps

    @classmethod
    def _contradiction_message(cls, witness: ContradictionWitness) -> str:
        if witness.kind is ContradictionKind.EMPTY_CELL and len(witness.cells) == 1:
            cell = witness.cells[0]
            return (
                "모순을 발견했습니다. "
                f"R{cell[0] + 1}C{cell[1] + 1}에 남은 후보가 없습니다."
            )

        if (
            witness.kind is ContradictionKind.MISSING_DIGIT
            and witness.unit_index is not None
            and len(witness.digits) == 1
        ):
            unit_name = cls._unit_name(witness.unit_index)
            value = min(witness.digits)
            return f"모순을 발견했습니다. {unit_name}에 숫자 {value}가 들어갈 곳이 없습니다."

        raise RuntimeError("구조가 잘못된 모순 witness입니다.")

    @staticmethod
    def _unit_name(unit_index: int) -> str:
        if unit_index < len(ROWS):
            return f"{unit_index + 1}행"
        if unit_index < len(ROWS) + len(COLS):
            return f"{unit_index - len(ROWS) + 1}열"
        return f"{unit_index - len(ROWS) - len(COLS) + 1}번 박스"

    @staticmethod
    def _step(
        kind: StepKind,
        snapshot: SudokuSnapshot,
        *,
        deduction: TechniqueResult | None = None,
        assumption: Assignment | None = None,
        contradiction: ContradictionWitness | None = None,
        message: str = "",
    ) -> SolveStep:
        grid, candidates = snapshot
        return SolveStep(
            kind=kind,
            grid=grid,
            candidates=candidates,
            deduction=deduction,
            assumption=assumption,
            contradiction=contradiction,
            message=message,
        )

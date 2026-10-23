"""Shared deduction, one-ply refutation, and bounded search execution."""

from dataclasses import dataclass, replace
from enum import Enum, auto
from typing import Protocol, Self


class LogicStatus(Enum):
    SOLVED = auto()
    STALLED = auto()
    CONTRADICTION = auto()


class EngineState[Snapshot, Witness](Protocol):
    def clone(self) -> Self: ...

    def snapshot(self) -> Snapshot: ...

    def find_contradiction(self) -> Witness | None: ...

    def is_complete(self) -> bool: ...


class EngineDomain[State, Snapshot, Deduction, Decision, Witness](Protocol):
    """Domain rules and ordering; execution belongs to Engine."""

    def find_deduction(self, snapshot: Snapshot) -> Deduction | None: ...

    def apply_deduction(self, state: State, deduction: Deduction) -> None: ...

    def probe_candidates(self, snapshot: Snapshot) -> tuple[Decision, ...]: ...

    def probe_stalled(self, decision: Decision) -> None: ...

    def assume(self, state: State, decision: Decision) -> None: ...

    def refutation(self, decision: Decision, contradiction: Witness) -> Deduction: ...

    def search_candidates(self, snapshot: Snapshot) -> tuple[Decision, ...]: ...

    def solution_key(self, snapshot: Snapshot) -> object: ...


@dataclass(frozen=True, slots=True)
class LogicStep[Snapshot, Deduction]:
    before: Snapshot
    after: Snapshot
    deduction: Deduction


@dataclass(frozen=True, slots=True)
class LogicRun[Snapshot, Deduction, Witness]:
    status: LogicStatus
    initial_state: Snapshot
    final_state: Snapshot
    steps: tuple[LogicStep[Snapshot, Deduction], ...]
    contradiction: Witness | None = None


@dataclass(frozen=True, slots=True)
class ProbeRun[Snapshot, Deduction, Decision, Witness]:
    assumption: Decision
    logic_result: LogicRun[Snapshot, Deduction, Witness]


@dataclass(frozen=True, slots=True)
class ProbeRound[Snapshot, Deduction, Decision, Witness]:
    before: Snapshot
    candidates: tuple[Decision, ...]
    probes: tuple[ProbeRun[Snapshot, Deduction, Decision, Witness], ...]
    elimination: LogicRun[Snapshot, Deduction, Witness] | None = None


@dataclass(frozen=True, slots=True)
class SolveRun[Snapshot, Deduction, Decision, Witness]:
    initial_logic_result: LogicRun[Snapshot, Deduction, Witness]
    probing_rounds: tuple[ProbeRound[Snapshot, Deduction, Decision, Witness], ...]
    solutions: tuple[Snapshot, ...]
    used_backtrack_search: bool


class Engine[State: EngineState, Snapshot, Deduction, Decision, Witness]:
    """Run a domain's rules against its native mutable state and snapshots."""

    def __init__(
        self,
        domain: EngineDomain[State, Snapshot, Deduction, Decision, Witness],
    ) -> None:
        self.domain = domain

    def _apply(self, state: State, deduction: Deduction, before: Snapshot) -> Snapshot:
        self.domain.apply_deduction(state, deduction)
        after = state.snapshot()
        if after == before:
            raise RuntimeError("A deduction must change the state.")
        return after

    def propagate(
        self, state: State, record: bool = True
    ) -> LogicRun[Snapshot, Deduction, Witness]:
        """Mutate state until contradiction or a logical fixed point."""
        initial = before = state.snapshot()
        steps: list[LogicStep[Snapshot, Deduction]] = []
        while True:
            contradiction = state.find_contradiction()
            if contradiction is not None:
                status = LogicStatus.CONTRADICTION
                break
            deduction = self.domain.find_deduction(before)
            if deduction is None:
                status = (
                    LogicStatus.SOLVED if state.is_complete() else LogicStatus.STALLED
                )
                break
            after = self._apply(state, deduction, before)
            if record:
                steps.append(LogicStep(before, after, deduction))
            before = after
        return LogicRun(status, initial, before, tuple(steps), contradiction)

    def solve(
        self, state: State, solution_limit: int
    ) -> SolveRun[Snapshot, Deduction, Decision, Witness]:
        """Explain one-ply reasoning, then collect distinct solutions up to a cap."""
        if solution_limit <= 0:
            raise ValueError("solution_limit must be positive.")
        initial = current = self.propagate(state)
        rounds: list[ProbeRound[Snapshot, Deduction, Decision, Witness]] = []
        used_backtrack_search = False
        while current.status is LogicStatus.STALLED:
            before = state.snapshot()
            candidates = self.domain.probe_candidates(before)
            probes: list[ProbeRun[Snapshot, Deduction, Decision, Witness]] = []
            elimination = None
            decisive = None
            for decision in candidates:
                branch = state.clone()
                self.domain.assume(branch, decision)
                result = self.propagate(branch)
                probes.append(ProbeRun(decision, result))
                if result.status is LogicStatus.STALLED:
                    self.domain.probe_stalled(decision)
                    continue
                decisive = result
                if result.status is LogicStatus.CONTRADICTION:
                    if result.contradiction is None:
                        raise RuntimeError("A contradictory probe needs a witness.")
                    deduction = self.domain.refutation(decision, result.contradiction)
                    after = self._apply(state, deduction, before)
                    resumed = self.propagate(state)
                    elimination = decisive = replace(
                        resumed,
                        initial_state=before,
                        steps=(LogicStep(before, after, deduction), *resumed.steps),
                    )
                break
            rounds.append(ProbeRound(before, candidates, tuple(probes), elimination))
            if decisive is None:
                used_backtrack_search = True
                break
            current = decisive

        solutions = (
            [current.final_state] if current.status is LogicStatus.SOLVED else []
        )
        if current.status is not LogicStatus.CONTRADICTION:
            self._collect_solutions(state.clone(), solutions, solution_limit)
        return SolveRun(initial, tuple(rounds), tuple(solutions), used_backtrack_search)

    def _collect_solutions(
        self, state: State, solutions: list[Snapshot], limit: int
    ) -> None:
        """Search silently; visible probe ordering and history stay untouched."""
        if len(solutions) >= limit:
            return
        result = self.propagate(state, record=False)
        if result.status is LogicStatus.CONTRADICTION:
            return
        if result.status is LogicStatus.SOLVED:
            key = self.domain.solution_key(result.final_state)
            if all(self.domain.solution_key(existing) != key for existing in solutions):
                solutions.append(result.final_state)
            return
        for decision in self.domain.search_candidates(result.final_state):
            if len(solutions) >= limit:
                return
            branch = state.clone()
            self.domain.assume(branch, decision)
            self._collect_solutions(branch, solutions, limit)

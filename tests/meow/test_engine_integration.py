from meow.logic_solver import solve_logically
from meow.puzzle_catalog import load_preset
from meow.solve_types import LogicStatus
from meow.solver import SolveOutcome, solve
from meow.state import LogicState


def test_public_solve_runs_shared_engine_probing(monkeypatch) -> None:
    from puzzle_common.engine import Engine

    original = Engine.solve
    runs = []

    def solve_and_record(self, state, *, solution_limit):
        run = original(self, state, solution_limit=solution_limit)
        runs.append(run)
        return run

    monkeypatch.setattr(Engine, "solve", solve_and_record)

    result = solve(load_preset("전문가"))

    assert len(runs) == 1
    assert runs[0].probing_rounds
    assert runs[0].solutions
    assert result.outcome is SolveOutcome.SOLVED_WITH_PROBING
    assert result.probing_rounds[0].probes[0].assumption == (0, 2)
    assert result.solution == tuple(sorted(runs[0].solutions[0].cats))


def test_logical_entry_uses_shared_engine_without_mutating_input(monkeypatch) -> None:
    from puzzle_common.engine import Engine

    puzzle = load_preset("보통")
    state = LogicState(puzzle)
    state.place_cat((0, 0))
    before = state.snapshot()
    original = Engine.propagate
    states = []

    def propagate_and_record(self, working, *, record=True):
        states.append(working)
        return original(self, working, record=record)

    monkeypatch.setattr(Engine, "propagate", propagate_and_record)

    result = solve_logically(puzzle, state)

    assert len(states) == 1
    assert states[0] is not state
    assert state.snapshot() == before
    assert result.initial_state == before
    assert result.status is LogicStatus.SOLVED_LOGICALLY
    assert len(result.final_state.cats) == 7
    assert result.steps

from meow.logic_solver import solve_logically
from meow.puzzle_catalog import load_preset
from meow.solver import solve


def test_solver_returns_common_result_with_unconverted_engine_run(monkeypatch):
    from puzzle_common.engine import Engine, Outcome, SolveResult

    original = Engine.solve
    runs = []

    def record_run(self, state, solution_limit):
        run = original(self, state, solution_limit)
        runs.append(run)
        return run

    monkeypatch.setattr(Engine, "solve", record_run)

    result = solve(load_preset("전문가"))

    assert type(result) is SolveResult
    assert result.run is runs[0]
    assert result.outcome is Outcome.UNIQUE
    assert result.solution is result.run.solutions[0]
    assert result.run.probing_rounds[0].probes[0].assumption == (0, 2)


def test_logic_returns_the_shared_run_without_conversion(monkeypatch):
    from puzzle_common.engine import Engine

    original = Engine.propagate
    runs = []

    def record_run(self, state, record=True):
        run = original(self, state, record)
        runs.append(run)
        return run

    monkeypatch.setattr(Engine, "propagate", record_run)

    result = solve_logically(load_preset("쉬움"))

    assert result is runs[0]


def test_app_uses_public_solver_directly():
    from meow.definition import DEFINITION

    assert DEFINITION.solve is solve

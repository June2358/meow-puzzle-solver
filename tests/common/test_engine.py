"""Shared control flow tested with a small deterministic state graph."""

from dataclasses import dataclass, field

import pytest

from puzzle_common.engine import Engine, LogicStatus


@dataclass
class State:
    node: str

    def clone(self):
        return State(self.node)

    def snapshot(self):
        return self.node

    def find_contradiction(self):
        return self.node if self.node.startswith("bad") else None

    def is_complete(self):
        return self.node.startswith("solved")


@dataclass
class Domain:
    deductions: dict[str, str] = field(default_factory=dict)
    probes: dict[str, tuple[str, ...]] = field(default_factory=dict)
    refutations: dict[str, str] = field(default_factory=dict)
    branches: dict[str, tuple[str, ...]] = field(default_factory=dict)
    calls: list[tuple[str, str]] = field(default_factory=list)

    def find_deduction(self, snapshot):
        self.calls.append(("find", snapshot))
        return self.deductions.get(snapshot)

    def apply_deduction(self, state, deduction):
        state.node = deduction

    def probe_candidates(self, snapshot):
        self.calls.append(("rank", snapshot))
        return self.probes.get(snapshot, ())

    def probe_stalled(self, decision):
        self.calls.append(("stall", decision))

    def assume(self, state, decision):
        self.calls.append(("assume", decision))
        state.node = decision

    def refutation(self, decision, contradiction):
        assert decision == contradiction
        return self.refutations[decision]

    def search_candidates(self, snapshot):
        self.calls.append(("search", snapshot))
        return self.branches.get(snapshot, ())

    def solution_key(self, snapshot):
        return snapshot.split(":")[0]


@pytest.mark.parametrize(
    ("node", "status"),
    [("root", LogicStatus.STALLED), ("bad", LogicStatus.CONTRADICTION)],
)
def test_propagation_terminal_status(node, status):
    domain = Domain()
    result = Engine(domain).propagate(State(node))
    assert result.status is status
    assert result.initial_state == result.final_state == node
    assert result.steps == ()
    assert result.contradiction == (node if node == "bad" else None)
    assert ("find", "bad") not in domain.calls


def test_propagation_applies_deduction_before_checking_completeness():
    domain = Domain(deductions={"root": "solved-raw", "solved-raw": "solved-clean"})
    state = State("root")
    result = Engine(domain).propagate(state)
    assert result.status is LogicStatus.SOLVED
    assert result.initial_state == "root"
    assert result.final_state == state.node == "solved-clean"
    assert [(s.before, s.after, s.deduction) for s in result.steps] == [
        ("root", "solved-raw", "solved-raw"),
        ("solved-raw", "solved-clean", "solved-clean"),
    ]


def test_no_op_deduction_is_rejected():
    with pytest.raises(RuntimeError, match="change"):
        Engine(Domain(deductions={"root": "root"})).propagate(State("root"))


def test_first_decisive_probe_refutes_then_restarts_with_fresh_ranking():
    domain = Domain(
        deductions={"refuted": "next"},
        probes={"root": ("stall", "bad-one", "unused"), "next": ("solved-one",)},
        refutations={"bad-one": "refuted"},
    )
    state = State("root")
    result = Engine(domain).solve(state, solution_limit=1)
    assert result.solutions == ("solved-one",)
    assert not result.used_backtrack_search
    assert state.node == "next"
    first, second = result.probing_rounds
    assert first.before == "root"
    assert first.candidates == ("stall", "bad-one", "unused")
    assert [probe.assumption for probe in first.probes] == ["stall", "bad-one"]
    assert first.probes[0].logic_result.initial_state == "stall"
    assert first.elimination.initial_state == "root"
    assert first.elimination.final_state == "next"
    assert [(s.before, s.after) for s in first.elimination.steps] == [
        ("root", "refuted"),
        ("refuted", "next"),
    ]
    assert second.before == "next"
    assert [(kind, node) for kind, node in domain.calls if kind == "rank"] == [
        ("rank", "root"),
        ("rank", "next"),
    ]
    assert [(kind, node) for kind, node in domain.calls if kind == "stall"] == [
        ("stall", "stall")
    ]
    assert ("assume", "unused") not in domain.calls


@pytest.mark.parametrize("probes", [(), ("stall",)])
def test_exhausted_probe_round_enters_recursive_silent_search(probes):
    domain = Domain(
        probes={"root": probes, "branch": ("must-not-probe",)},
        branches={"root": ("bad-search", "branch"), "branch": ("solved-one",)},
    )
    result = Engine(domain).solve(State("root"), solution_limit=1)
    assert result.used_backtrack_search
    assert result.solutions == ("solved-one",)
    assert len(result.probing_rounds) == 1
    assert result.probing_rounds[0].candidates == probes
    assert result.probing_rounds[0].elimination is None
    assert [node for kind, node in domain.calls if kind == "rank"] == ["root"]
    assert [node for kind, node in domain.calls if kind == "stall"] == list(probes)


def test_preferred_solution_is_retained_deduplicated_and_counted_to_limit():
    domain = Domain(
        probes={"root": ("solved-one:preferred",)},
        branches={"root": ("solved-one:search", "solved-two", "solved-unused")},
    )
    result = Engine(domain).solve(State("root"), solution_limit=2)
    assert result.solutions == ("solved-one:preferred", "solved-two")
    assert not result.used_backtrack_search
    assert ("assume", "solved-unused") not in domain.calls


@pytest.mark.parametrize("terminal", ["solved-one", "bad-root"])
def test_initial_terminal_state_needs_no_probes_or_fallback(terminal):
    domain = Domain()
    result = Engine(domain).solve(State(terminal), solution_limit=1)
    assert result.solutions == ((terminal,) if terminal.startswith("solved") else ())
    assert result.probing_rounds == ()
    assert not result.used_backtrack_search
    assert all(kind not in ("rank", "search", "assume") for kind, _ in domain.calls)


def test_refutation_contradiction_ends_reasoning_without_search():
    domain = Domain(
        probes={"root": ("bad-probe",)}, refutations={"bad-probe": "bad-root"}
    )
    result = Engine(domain).solve(State("root"), solution_limit=1)
    assert result.solutions == ()
    assert result.probing_rounds[0].elimination.status is LogicStatus.CONTRADICTION
    assert not result.used_backtrack_search


def test_unrecorded_propagation_keeps_no_steps():
    result = Engine(Domain(deductions={"root": "solved-one"})).propagate(
        State("root"), record=False
    )
    assert result.status is LogicStatus.SOLVED
    assert result.final_state == "solved-one"
    assert result.steps == ()


@pytest.mark.parametrize("limit", [0, -1])
def test_nonpositive_solution_limit_is_rejected(limit):
    with pytest.raises(ValueError, match="positive"):
        Engine(Domain()).solve(State("root"), solution_limit=limit)

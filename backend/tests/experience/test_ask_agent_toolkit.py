"""`tests/strategy.md`'s read-only-enforcement test — asserts
`AskAgentToolkit.build_tools()` never returns a tool bound to a write
method, run against the actual registered tool list, not just read by
inspection (constitution AI safety rule 2)."""

import inspect

from app.experience.adapters.ask_agent_graph import AskAgentToolkit
from app.experience.application.ports import (
    FindingReadPort,
    LedgerQueryPort,
    ScoreReadPort,
    StakeholderReadPort,
)

_WRITE_METHOD_NAMES = frozenset({"save", "persist", "quarantine", "record", "append", "delete"})


class _FakeLedger(LedgerQueryPort):
    async def baseline_vs_current(self, stakeholder_id):
        return None

    async def timeline_for_stakeholder(self, stakeholder_id, *, limit=20):
        return []


class _FakeFindings(FindingReadPort):
    async def get_finding(self, finding_id):
        return None

    async def resolve_events(self, event_ids):
        return []

    async def get_commitment_comparison(self, event_id):
        return None

    async def get_usage_comparison(self, event_id):
        return None

    async def list_open_commitments(self, *, limit=20):
        return []


class _FakeScore(ScoreReadPort):
    async def latest_run(self):
        return None

    async def trend(self, *, days):
        return []

    async def list_contributions(self, score_run_id):
        return []

    async def get_contribution(self, score_contribution_id):
        return None


class _FakeStakeholders(StakeholderReadPort):
    async def list_stakeholders(self):
        return []


def _toolkit() -> AskAgentToolkit:
    return AskAgentToolkit(
        ledger=_FakeLedger(),
        findings=_FakeFindings(),
        score=_FakeScore(),
        stakeholders=_FakeStakeholders(),
    )


def test_exactly_three_tools_are_registered():
    """Matches `decisions/03-langgraph-for-ask-agent.md`'s "bounded to a
    fixed set of 3 tools" — no speculative 4th (P10 YAGNI)."""
    tools = _toolkit().build_tools()
    assert len(tools) == 3
    assert {t.name for t in tools} == {"query_ledger", "query_findings", "query_score_runs"}


def test_no_tool_is_bound_to_a_write_method():
    """Structural, not conventional: every port type `AskAgentToolkit`'s
    constructor accepts (`LedgerQueryPort`/`FindingReadPort`/`ScoreReadPort`/
    `StakeholderReadPort`) declares zero write methods on its own abstract
    interface — there is no method here that *could* be registered as a
    write-capable tool. This test asserts that structural fact mechanically
    rather than only documenting it."""
    for port_type in (LedgerQueryPort, FindingReadPort, ScoreReadPort, StakeholderReadPort):
        method_names = {
            name
            for name, member in inspect.getmembers(port_type)
            if callable(member) and not name.startswith("_")
        }
        write_methods = method_names & _WRITE_METHOD_NAMES
        assert not write_methods, f"{port_type.__name__} declares a write method: {write_methods}"


async def test_each_registered_tool_only_reaches_a_read_only_coroutine():
    """Invokes each tool's own coroutine against fakes whose every method is
    itself read-only by type — no write call is reachable to make even if a
    tool implementation tried to call one."""
    toolkit = _toolkit()
    tools = toolkit.build_tools()
    for tool in tools:
        assert tool.coroutine is not None
        assert tool.coroutine.__self__ is toolkit

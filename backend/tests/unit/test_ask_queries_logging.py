"""FR-023 — every terminal node (render, handoff, decline x2, fallback)
produces exactly one `ask_queries` row with the correct `matched_intent`/
`rendered_component`/`declined_reason` combination. Reuses
`tests/experience/test_ask_agent_graph.py`'s fakes rather than duplicating
them."""

from uuid import uuid4

from app.experience.adapters.ask_agent_graph import Intent
from tests.experience.test_ask_agent_graph import (
    _build_graph,
    _contribution,
    _FakeAskQueries,
    _FakeLLM,
    _FakeScore,
    _run,
    _ScoreRun,
)


async def test_render_path_logs_matched_intent_and_component():
    run = _ScoreRun()
    ask_queries = _FakeAskQueries()
    graph = _build_graph(
        _FakeLLM(Intent.SCORE_DELTA),
        score=_FakeScore(latest=run, contributions=[_contribution()]),
        ask_queries=ask_queries,
    )
    await _run(graph, "why did the score go up?")
    assert len(ask_queries.logged) == 1
    row = ask_queries.logged[0]
    assert row["matched_intent"] == "score_delta"
    assert row["rendered_component"] == "delta_breakdown"
    assert row["declined_reason"] is None


async def test_handoff_path_logs_matched_intent_and_draft_handoff_component():
    run = _ScoreRun()
    ask_queries = _FakeAskQueries()
    graph = _build_graph(
        _FakeLLM(Intent.WRITE_TO_STAKEHOLDER),
        score=_FakeScore(latest=run, contributions=[_contribution()]),
        ask_queries=ask_queries,
    )
    await _run(graph, "write to Ana about this")
    row = ask_queries.logged[0]
    assert row["matched_intent"] == "write_to_stakeholder"
    assert row["rendered_component"] == "draft_handoff"
    assert row["declined_reason"] is None


async def test_decline_path_logs_no_matched_intent_only_declined_reason():
    """`data-base/08-schema-experience.md`'s own worked example: "Will
    Meridian actually cancel?" logs `matched_intent = NULL`, `declined_
    reason = prediction` — `prediction`/`colleague_judgment` are real
    classify outcomes but not REQ-M9-02 "matches" (found and fixed while
    writing this exact test)."""
    ask_queries = _FakeAskQueries()
    graph = _build_graph(_FakeLLM(Intent.PREDICTION), ask_queries=ask_queries)
    await _run(graph, "will they cancel?")
    row = ask_queries.logged[0]
    assert row["matched_intent"] is None
    assert row["rendered_component"] is None
    assert row["declined_reason"] == "prediction"


async def test_fallback_path_logs_unclear_with_no_intent_or_component():
    ask_queries = _FakeAskQueries()
    graph = _build_graph(_FakeLLM(Intent.NONE), ask_queries=ask_queries)
    await _run(graph, "what's the weather?")
    row = ask_queries.logged[0]
    assert row["matched_intent"] is None
    assert row["rendered_component"] is None
    assert row["declined_reason"] == "unclear"


async def test_response_time_is_always_recorded():
    ask_queries = _FakeAskQueries()
    graph = _build_graph(_FakeLLM(Intent.PREDICTION), ask_queries=ask_queries)
    await graph.ainvoke(
        {"question": "will they cancel?", "asked_by_user_id": uuid4(), "started_at": 0.0}
    )
    assert ask_queries.logged[0]["response_time_ms"] >= 0

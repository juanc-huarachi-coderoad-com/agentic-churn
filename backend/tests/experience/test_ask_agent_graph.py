"""`tests/strategy.md`'s "Ask agent (LangGraph) tests" — branch coverage: one
test per REQ-M9-02 intent plus decline/fallback/handoff, the compiled graph
invoked directly with a fixed `AskAgentState` and fake ports. No real tool
execution, no real model call — `LLMPort` and the toolkit's ports are both
fakes."""

from datetime import UTC, datetime
from typing import Any, TypeVar
from uuid import UUID, uuid4

from app.experience.adapters.ask_agent_graph import (
    AskAgentToolkit,
    ClassifyOutput,
    Intent,
    build_ask_agent_graph,
)
from app.experience.domain.entities import CommitmentStatusRecord, ContributionRecord
from app.readers.application.ports import LLMPort
from app.readers.domain.entities import ConfirmedBaselineWindow, MessageEventInfo

T = TypeVar("T")


class _FakeLLM(LLMPort):
    def __init__(self, intent: Intent, subject_hint: str | None = None) -> None:
        self._intent = intent
        self._subject_hint = subject_hint

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        return ClassifyOutput(intent=self._intent, subject_hint=self._subject_hint)  # type: ignore[return-value]


class _FakeLedger:
    def __init__(
        self,
        baseline: tuple[ConfirmedBaselineWindow, list[MessageEventInfo]] | None = None,
        timeline: list[MessageEventInfo] | None = None,
    ) -> None:
        self._baseline = baseline
        self._timeline = timeline or []

    async def baseline_vs_current(self, stakeholder_id: UUID):
        return self._baseline

    async def timeline_for_stakeholder(self, stakeholder_id: UUID, *, limit: int = 20):
        return self._timeline


class _FakeFindings:
    def __init__(self, commitments: list[Any] | None = None) -> None:
        self._commitments = commitments or []

    async def list_open_commitments(self, *, limit: int = 20):
        return self._commitments


class _FakeScore:
    def __init__(
        self, latest: Any = None, contributions: list[ContributionRecord] | None = None
    ) -> None:
        self._latest = latest
        self._contributions = contributions or []

    async def latest_run(self):
        return self._latest

    async def list_contributions(self, score_run_id: UUID):
        return self._contributions


class _FakeStakeholders:
    def __init__(self, stakeholders: list[Any] | None = None) -> None:
        self._stakeholders = stakeholders or []

    async def list_stakeholders(self):
        return self._stakeholders


class _Stakeholder:
    def __init__(self, name: str, role: str = "CTO", last_seen_at: datetime | None = None) -> None:
        self.stakeholder_id = uuid4()
        self.name = name
        self.role = role
        self.last_seen_at = last_seen_at


class _ScoreRun:
    def __init__(self, score: float = 61.0, band: str = "at_risk") -> None:
        self.id = uuid4()
        self.score = score
        self.band = band


class _FakeNarrator:
    def __init__(self, latest: Any = None) -> None:
        self._latest = latest

    async def get_latest(self):
        return self._latest

    async def get_for_score_run(self, score_run_id: UUID):
        return None


class _NarratorSummary:
    def __init__(self, actions: tuple[dict[str, object], ...]) -> None:
        self.headline = "h"
        self.reasons = ()
        self.actions = actions


class _FakeCoverage:
    def __init__(self, sources: list[Any] | None = None) -> None:
        self._sources = sources if sources is not None else []

    async def list_sources(self):
        return self._sources


class _Source:
    def __init__(self, source_type: str, status: str) -> None:
        self.source_type = source_type
        self.status = status


class _FakeAskQueries:
    def __init__(self) -> None:
        self.logged: list[dict[str, Any]] = []

    async def log(self, **kwargs: Any) -> None:
        self.logged.append(kwargs)


def _contribution(finding_type: str = "broken_response_promise", points: float = -39.0):
    return ContributionRecord(
        id=uuid4(),
        finding_id=uuid4(),
        finding_type=finding_type,
        points_contributed=points,
        is_positive=points > 0,
        base=1,
        influence=1,
        criticality=1,
        confidence=1,
        magnitude=1,
        recency=1,
        damping=1,
        rank_within_issue_factor=1,
        issue_id=uuid4(),
    )


def _build_graph(
    llm: LLMPort,
    *,
    ledger: Any = None,
    findings: Any = None,
    score: Any = None,
    stakeholders: Any = None,
    narrator: Any = None,
    coverage: Any = None,
    ask_queries: Any = None,
):
    toolkit = AskAgentToolkit(
        ledger=ledger or _FakeLedger(),
        findings=findings or _FakeFindings(),
        score=score or _FakeScore(),
        stakeholders=stakeholders or _FakeStakeholders(),
    )
    return build_ask_agent_graph(
        llm,
        toolkit,
        narrator or _FakeNarrator(),
        coverage or _FakeCoverage(),
        ask_queries or _FakeAskQueries(),
    )


async def _run(graph: Any, question: str = "a question?") -> dict[str, Any]:
    return await graph.ainvoke(
        {"question": question, "asked_by_user_id": uuid4(), "started_at": 0.0}
    )


async def test_score_delta_renders_delta_breakdown():
    run = _ScoreRun()
    graph = _build_graph(
        _FakeLLM(Intent.SCORE_DELTA), score=_FakeScore(latest=run, contributions=[_contribution()])
    )
    result = await _run(graph)
    assert result["component"] == "delta_breakdown"
    assert result["component_props"]["score"] == 61.0
    assert len(result["sources"]) > 0  # REQ-M9-P3 — never an uncited claim


async def test_top_risk_renders_ranked_issues():
    run = _ScoreRun()
    graph = _build_graph(
        _FakeLLM(Intent.TOP_RISK), score=_FakeScore(latest=run, contributions=[_contribution()])
    )
    result = await _run(graph)
    assert result["component"] == "ranked_issues"
    assert len(result["component_props"]["ranked_issues"]) == 1
    assert len(result["sources"]) > 0  # REQ-M9-P3 — never an uncited claim


async def test_quiet_stakeholders_renders_stakeholder_cards():
    graph = _build_graph(
        _FakeLLM(Intent.QUIET_STAKEHOLDERS),
        stakeholders=_FakeStakeholders([_Stakeholder("Diego Marín")]),
    )
    result = await _run(graph)
    assert result["component"] == "stakeholder_cards"
    assert result["component_props"]["stakeholders"][0]["name"] == "Diego Marín"
    assert len(result["sources"]) > 0  # REQ-M9-P3 — never an uncited claim


async def test_recommended_actions_renders_action_checklist_from_narrator():
    actions = ({"text": "Escalate", "owner": "Marta", "due_date": "2026-08-16"},)
    graph = _build_graph(
        _FakeLLM(Intent.RECOMMENDED_ACTIONS), narrator=_FakeNarrator(_NarratorSummary(actions))
    )
    result = await _run(graph)
    assert result["component"] == "action_checklist"
    assert result["component_props"]["actions"] == list(actions)


async def test_recommended_actions_with_no_narration_yet_falls_back():
    graph = _build_graph(_FakeLLM(Intent.RECOMMENDED_ACTIONS), narrator=_FakeNarrator(None))
    result = await _run(graph)
    assert result.get("component") is None
    assert result["declined_reason"] == "unclear"


async def test_commitments_status_renders_commitments():
    commitment = CommitmentStatusRecord(
        event_id=uuid4(),
        occurred_at=datetime.now(UTC),
        quoted_text="promise",
        state="open",
        business_hours_elapsed=2.0,
        threshold_business_hours=4.0,
    )
    graph = _build_graph(
        _FakeLLM(Intent.COMMITMENTS_STATUS), findings=_FakeFindings(commitments=[commitment])
    )
    result = await _run(graph)
    assert result["component"] == "commitments_status"
    assert result["component_props"]["commitments"][0]["text"] == "promise"


async def test_baseline_check_renders_baseline_comparison():
    window = ConfirmedBaselineWindow(
        stakeholder_id=uuid4(),
        window_start=datetime.now(UTC),
        window_end=datetime.now(UTC),
        sample_texts=("a", "b", "c", "d", "e"),
    )
    graph = _build_graph(
        _FakeLLM(Intent.BASELINE_CHECK, subject_hint="Ana"),
        ledger=_FakeLedger(baseline=(window, [])),
        stakeholders=_FakeStakeholders([_Stakeholder("Ana Reyes")]),
        coverage=_FakeCoverage([_Source("gmail", "connected")]),
    )
    result = await _run(graph)
    assert result["component"] == "baseline_comparison"
    assert result["component_props"]["baseline_sample_count"] == 5


async def test_timeline_renders_filtered_timeline():
    event = MessageEventInfo(
        event_id=uuid4(), occurred_at=datetime.now(UTC), stakeholder_id=uuid4(), text="hi"
    )
    graph = _build_graph(
        _FakeLLM(Intent.TIMELINE, subject_hint="Ana"),
        ledger=_FakeLedger(timeline=[event]),
        stakeholders=_FakeStakeholders([_Stakeholder("Ana Reyes")]),
        coverage=_FakeCoverage([_Source("gmail", "connected")]),
    )
    result = await _run(graph)
    assert result["component"] == "filtered_timeline"
    assert len(result["component_props"]["events"]) == 1


async def test_write_to_stakeholder_produces_a_handoff_not_an_inline_answer():
    """FR-012a — a distinct handoff response, not a rendered component,
    not a fallback."""
    run = _ScoreRun()
    graph = _build_graph(
        _FakeLLM(Intent.WRITE_TO_STAKEHOLDER, subject_hint="Ana"),
        score=_FakeScore(latest=run, contributions=[_contribution()]),
        stakeholders=_FakeStakeholders([_Stakeholder("Ana Reyes")]),
    )
    result = await _run(graph)
    assert result["component"] == "draft_handoff"
    assert result["component_props"]["stakeholder_id"] is not None
    assert result["component_props"]["issue_id"] is not None


async def test_unknown_person_produces_a_fallback_not_a_guess():
    graph = _build_graph(
        _FakeLLM(Intent.BASELINE_CHECK, subject_hint="Nobody"),
        coverage=_FakeCoverage([_Source("gmail", "connected")]),
    )
    result = await _run(graph)
    assert result.get("component") is None
    assert result["declined_reason"] == "unclear"


# ---------------------------------------------------------------------------
# US3 — decline / fallback / insufficient_history / source_not_connected
# (T037: extends this file per tasks.md, rather than a separate one)
# ---------------------------------------------------------------------------


async def test_prediction_question_declines_never_a_probability():
    graph = _build_graph(_FakeLLM(Intent.PREDICTION))
    result = await _run(graph, "will they cancel?")
    assert result["declined_reason"] == "prediction"
    assert result.get("component") is None
    assert "forecast" in result["fallback_text"]


async def test_colleague_judgment_declines_never_a_character_assessment():
    graph = _build_graph(_FakeLLM(Intent.COLLEAGUE_JUDGMENT))
    result = await _run(graph, "is Bob doing a good job?")
    assert result["declined_reason"] == "colleague_judgment"
    assert result.get("component") is None


async def test_no_matching_intent_falls_back_with_sources():
    graph = _build_graph(_FakeLLM(Intent.NONE))
    result = await _run(graph, "what's the weather like?")
    assert result["declined_reason"] == "unclear"
    assert result.get("component") is None
    assert "fallback_text" in result


async def test_insufficient_history_stakeholder_declines_distinctly_from_source_not_connected():
    graph = _build_graph(
        _FakeLLM(Intent.BASELINE_CHECK, subject_hint="Diego"),
        ledger=_FakeLedger(baseline=None),  # fewer than 5 confirmed-baseline messages
        stakeholders=_FakeStakeholders([_Stakeholder("Diego Marín")]),
        coverage=_FakeCoverage([_Source("gmail", "connected")]),
    )
    result = await _run(graph, "is this normal for Diego?")
    assert result["declined_reason"] == "insufficient_history"
    assert result["declined_reason"] != "source_not_connected"


async def test_disconnected_message_sources_decline_as_source_not_connected():
    graph = _build_graph(
        _FakeLLM(Intent.QUIET_STAKEHOLDERS),
        coverage=_FakeCoverage(
            [_Source("gmail", "disconnected"), _Source("zendesk", "disconnected")]
        ),
    )
    result = await _run(graph, "who's gone quiet?")
    assert result["declined_reason"] == "source_not_connected"
    assert result.get("component") is None


async def test_every_terminal_node_logs_exactly_one_ask_queries_row():
    ask_queries = _FakeAskQueries()
    graph = _build_graph(_FakeLLM(Intent.PREDICTION), ask_queries=ask_queries)
    await _run(graph, "will they cancel?")
    assert len(ask_queries.logged) == 1
    assert ask_queries.logged[0]["declined_reason"] == "prediction"
    assert ask_queries.logged[0]["matched_intent"] is None

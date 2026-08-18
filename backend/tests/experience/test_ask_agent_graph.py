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
    LangGraphAskAgent,
    ResponseMode,
    TextGenerationOutput,
    build_ask_agent_graph,
)
from app.experience.domain.entities import (
    CommitmentStatusRecord,
    ComponentPart,
    ContributionRecord,
    TextPart,
)
from app.readers.application.ports import LLMPort
from app.readers.domain.entities import ConfirmedBaselineWindow, MessageEventInfo

T = TypeVar("T")


class _FakeLLM(LLMPort):
    """specs/014-ask-agent-response-formats — dispatches on `schema` so the
    same fake can stand in for both the classify call (`ClassifyOutput`)
    and the text-generation call (`TextGenerationOutput`), matching how the
    real graph makes two separate `generate_structured` calls."""

    def __init__(
        self,
        intent: Intent,
        subject_hint: str | None = None,
        response_mode: ResponseMode = ResponseMode.COMPONENT_ONLY,
        text_markdown: str | Exception | None = None,
    ) -> None:
        self._intent = intent
        self._subject_hint = subject_hint
        self._response_mode = response_mode
        self._text_markdown = text_markdown

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        if schema is TextGenerationOutput:
            if isinstance(self._text_markdown, Exception):
                raise self._text_markdown
            return TextGenerationOutput(markdown=self._text_markdown or "")  # type: ignore[return-value]
        return ClassifyOutput(  # type: ignore[return-value]
            intent=self._intent,
            subject_hint=self._subject_hint,
            response_mode=self._response_mode,
        )


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


def _build_agent(
    llm: LLMPort,
    *,
    ledger: Any = None,
    findings: Any = None,
    score: Any = None,
    stakeholders: Any = None,
    narrator: Any = None,
    coverage: Any = None,
    ask_queries: Any = None,
) -> LangGraphAskAgent:
    """specs/014-ask-agent-response-formats — mirrors `_build_graph`, but
    returns the `LangGraphAskAgent` wrapper so `.answer()`'s `parts`
    assembly (not just the raw graph state) can be asserted against."""
    toolkit = AskAgentToolkit(
        ledger=ledger or _FakeLedger(),
        findings=findings or _FakeFindings(),
        score=score or _FakeScore(),
        stakeholders=stakeholders or _FakeStakeholders(),
    )
    return LangGraphAskAgent(
        llm=llm,
        toolkit=toolkit,
        narrator=narrator or _FakeNarrator(),
        coverage=coverage or _FakeCoverage(),
        ask_queries=ask_queries or _FakeAskQueries(),
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


# ---------------------------------------------------------------------------
# specs/014-ask-agent-response-formats — response_mode / text generation /
# fact-check / hybrid (User Stories 1 and 3)
# ---------------------------------------------------------------------------


async def test_text_only_response_produces_a_single_text_part_no_component():
    run = _ScoreRun(score=61.0, band="at_risk")
    agent = _build_agent(
        _FakeLLM(
            Intent.SCORE_DELTA,
            response_mode=ResponseMode.TEXT_ONLY,
            text_markdown="The score is 61.0, which is at_risk.",
        ),
        score=_FakeScore(latest=run, contributions=[_contribution()]),
    )
    result = await agent.answer("why does this matter?", asked_by_user_id=uuid4())

    assert result.response_mode == "text_only"
    assert len(result.parts) == 1
    assert isinstance(result.parts[0], TextPart)
    assert result.parts[0].markdown == "The score is 61.0, which is at_risk."


async def test_hybrid_response_produces_text_then_component_from_one_snapshot():
    run = _ScoreRun(score=61.0, band="at_risk")
    agent = _build_agent(
        _FakeLLM(
            Intent.SCORE_DELTA,
            response_mode=ResponseMode.HYBRID,
            text_markdown="The score is 61.0, which is at_risk.",
        ),
        score=_FakeScore(latest=run, contributions=[_contribution()]),
    )
    result = await agent.answer(
        "what's driving this and what should I do?", asked_by_user_id=uuid4()
    )

    assert result.response_mode == "hybrid"
    assert len(result.parts) == 2
    assert isinstance(result.parts[0], TextPart)
    assert isinstance(result.parts[1], ComponentPart)
    assert result.parts[1].component == "delta_breakdown"
    # FR-008 — text and component agree because both came from the same
    # already-fetched component_props, never a second, separate fetch.
    assert result.parts[1].component_props["score"] == 61.0


async def test_component_only_stays_a_single_component_part_unchanged():
    run = _ScoreRun(score=61.0, band="at_risk")
    agent = _build_agent(
        _FakeLLM(Intent.SCORE_DELTA, response_mode=ResponseMode.COMPONENT_ONLY),
        score=_FakeScore(latest=run, contributions=[_contribution()]),
    )
    result = await agent.answer("why did the score go up?", asked_by_user_id=uuid4())

    assert result.response_mode == "component_only"
    assert len(result.parts) == 1
    assert isinstance(result.parts[0], ComponentPart)
    assert result.parts[0].component == "delta_breakdown"
    assert result.parts[0].component_props["score"] == 61.0


async def test_sentence_with_unverifiable_claim_is_dropped_not_shown():
    run = _ScoreRun(score=61.0, band="at_risk")
    agent = _build_agent(
        _FakeLLM(
            Intent.SCORE_DELTA,
            response_mode=ResponseMode.TEXT_ONLY,
            # The first sentence is real (61.0 is the actual score). The
            # second invents a stakeholder name and number nothing in
            # component_props supports — must be dropped, never shown.
            text_markdown=(
                "The score is 61.0. Fabricatington personally called the CEO 823 times about this."
            ),
        ),
        score=_FakeScore(latest=run, contributions=[_contribution()]),
    )
    result = await agent.answer("why does this matter?", asked_by_user_id=uuid4())

    assert len(result.parts) == 1
    markdown = result.parts[0].markdown  # type: ignore[union-attr]
    assert "61.0" in markdown
    assert "Fabricatington" not in markdown
    assert "823" not in markdown


async def test_text_generation_failure_degrades_to_component_only():
    run = _ScoreRun(score=61.0, band="at_risk")
    agent = _build_agent(
        _FakeLLM(
            Intent.SCORE_DELTA,
            response_mode=ResponseMode.TEXT_ONLY,
            text_markdown=TimeoutError("simulated LLM timeout"),
        ),
        score=_FakeScore(latest=run, contributions=[_contribution()]),
    )
    result = await agent.answer("why does this matter?", asked_by_user_id=uuid4())

    # Never an empty parts list, never a raised exception reaching the
    # caller — a real, complete component is what the CS manager sees.
    assert len(result.parts) == 1
    assert isinstance(result.parts[0], ComponentPart)
    assert result.parts[0].component == "delta_breakdown"


async def test_a_response_with_no_survivable_text_also_degrades_to_component_only():
    run = _ScoreRun(score=61.0, band="at_risk")
    agent = _build_agent(
        _FakeLLM(
            Intent.SCORE_DELTA,
            response_mode=ResponseMode.TEXT_ONLY,
            # Every claim in this sentence is unverifiable — nothing
            # survives the fact-check, never an empty text part.
            text_markdown="Completely Madeupname said the score is 999.9.",
        ),
        score=_FakeScore(latest=run, contributions=[_contribution()]),
    )
    result = await agent.answer("why does this matter?", asked_by_user_id=uuid4())

    assert len(result.parts) == 1
    assert isinstance(result.parts[0], ComponentPart)


async def test_component_only_is_the_default_response_mode_logged():
    ask_queries = _FakeAskQueries()
    run = _ScoreRun(score=61.0, band="at_risk")
    agent = _build_agent(
        _FakeLLM(Intent.SCORE_DELTA),
        score=_FakeScore(latest=run, contributions=[_contribution()]),
        ask_queries=ask_queries,
    )
    await agent.answer("why did the score go up?", asked_by_user_id=uuid4())

    assert ask_queries.logged[0]["response_mode"] == "component_only"


async def test_decline_and_fallback_log_no_response_mode():
    ask_queries = _FakeAskQueries()
    agent = _build_agent(_FakeLLM(Intent.PREDICTION), ask_queries=ask_queries)
    await agent.answer("will they cancel?", asked_by_user_id=uuid4())

    assert ask_queries.logged[0]["response_mode"] is None

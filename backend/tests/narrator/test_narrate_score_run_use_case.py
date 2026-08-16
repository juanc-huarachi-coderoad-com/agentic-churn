"""`NarrateScoreRunUseCase` — `LLMPort` faked (fixed structured responses, no
live Anthropic call). Covers spec.md's User Story 1 acceptance scenarios
1-3, 5-7 and the Edge Cases' fallback-headline / no-findings behavior.
"""

from typing import Any, TypeVar
from uuid import UUID, uuid4

import pytest

from app.narrator.application.ports import (
    ClientContextPort,
    NarratorOutputRepositoryPort,
    PlaybookPort,
    PlaybookTemplate,
    ScoreContextPort,
)
from app.narrator.application.prompts.narration_v1 import (
    NarrationActionOutput,
    NarrationModelOutput,
    NarrationReasonOutput,
)
from app.narrator.application.use_cases import NarrateScoreRunUseCase
from app.narrator.domain.entities import IssueSummary, NarratorOutput, RankedContribution
from app.readers.application.ports import LLMPort

T = TypeVar("T")

_PLAYBOOK_ID = uuid4()


class _FakeLLM(LLMPort):
    def __init__(self, response: Any) -> None:
        self._response = response

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        return self._response


class _FakeScoreContext(ScoreContextPort):
    def __init__(self, contributions: list[RankedContribution]) -> None:
        self._contributions = contributions

    async def get_ranked_contributions(self, score_run_id: UUID) -> list[RankedContribution]:
        return self._contributions

    async def get_top_issue(self, score_run_id: UUID) -> IssueSummary | None:
        if not self._contributions:
            return None
        top = self._contributions[0]
        return IssueSummary(label=top.finding_type, points=abs(top.points))

    async def get_score_and_band(self, score_run_id: UUID) -> tuple[float, str] | None:
        return 61.0, "at_risk"


class _FakeClientContext(ClientContextPort):
    def __init__(self, numbers: frozenset[str], names: frozenset[str]) -> None:
        self._numbers = numbers
        self._names = names

    async def build_verified_facts(
        self, cited_event_ids: list[UUID]
    ) -> tuple[frozenset[str], frozenset[str]]:
        return self._numbers, self._names


class _FakePlaybook(PlaybookPort):
    async def list_active(self, finding_type: str) -> list[PlaybookTemplate]:
        return [
            PlaybookTemplate(
                id=_PLAYBOOK_ID,
                template_text="Escalate {ticket_ref} with engineering {when}",
                default_owner_role="Support lead",
                default_sla_days=1,
            )
        ]


class _FakeRepository(NarratorOutputRepositoryPort):
    def __init__(self) -> None:
        self.persisted: list[tuple[NarratorOutput, UUID]] = []

    async def persist(self, output: NarratorOutput, score_run_id: UUID) -> None:
        self.persisted.append((output, score_run_id))


def _contribution(finding_type: str = "broken_response_promise", points: float = -39.0):
    return RankedContribution(
        finding_id=uuid4(),
        finding_type=finding_type,
        points=points,
        is_positive=points > 0,
        cited_event_ids=(uuid4(),),
    )


async def test_fact_check_passing_output_produces_a_verified_narration():
    """Acceptance Scenarios 1-3."""
    contribution = _contribution()
    candidate = NarrationModelOutput(
        headline="We took 19 hours to reply — we promised 4.",
        reasons=[
            NarrationReasonOutput(
                text="We took 19 hours to reply.", points=39.0, evidence_event_ids=[]
            )
        ],
        actions=[
            NarrationActionOutput(
                text="Escalate the ticket with engineering today",
                owner="Marta",
                due_date="2026-08-16",
                playbook_id=str(_PLAYBOOK_ID),
            )
        ],
    )
    use_case = NarrateScoreRunUseCase(
        llm=_FakeLLM(candidate),
        score_context=_FakeScoreContext([contribution]),
        client_context=_FakeClientContext(
            numbers=frozenset({"19", "4", "39.0"}), names=frozenset()
        ),
        playbook=_FakePlaybook(),
        repository=(repo := _FakeRepository()),
    )

    output = await use_case.execute(uuid4())

    assert output is not None
    assert output.fact_check_passed is True
    assert output.headline == candidate.headline
    assert len(output.reasons) == 1
    assert len(output.actions) == 1
    assert repo.persisted == [(output, repo.persisted[0][1])]


async def test_reason_with_an_unverifiable_fact_is_discarded_others_kept():
    """Acceptance Scenarios 5-6."""
    contribution = _contribution()
    candidate = NarrationModelOutput(
        headline="We took 19 hours to reply.",
        reasons=[
            NarrationReasonOutput(
                text="We took 19 hours to reply.", points=39.0, evidence_event_ids=[]
            ),
            NarrationReasonOutput(
                text="Fabricated: Bob complained 999 times.", points=1.0, evidence_event_ids=[]
            ),
        ],
        actions=[],
    )
    use_case = NarrateScoreRunUseCase(
        llm=_FakeLLM(candidate),
        score_context=_FakeScoreContext([contribution]),
        client_context=_FakeClientContext(numbers=frozenset({"19"}), names=frozenset()),
        playbook=_FakePlaybook(),
        repository=_FakeRepository(),
    )

    output = await use_case.execute(uuid4())

    assert output is not None
    assert len(output.reasons) == 1
    assert output.reasons[0].text == "We took 19 hours to reply."


async def test_action_missing_owner_or_due_date_is_excluded():
    """Acceptance Scenario 4 (REQ-M7-05)."""
    contribution = _contribution()
    candidate = NarrationModelOutput(
        headline="We took 19 hours to reply.",
        reasons=[],
        actions=[
            NarrationActionOutput(
                text="Escalate it", owner="", due_date="", playbook_id=str(_PLAYBOOK_ID)
            ),
            NarrationActionOutput(
                text="Escalate it with Marta",
                owner="Marta",
                due_date="2026-08-16",
                playbook_id=str(_PLAYBOOK_ID),
            ),
        ],
    )
    use_case = NarrateScoreRunUseCase(
        llm=_FakeLLM(candidate),
        score_context=_FakeScoreContext([contribution]),
        client_context=_FakeClientContext(numbers=frozenset({"19"}), names=frozenset({"Marta"})),
        playbook=_FakePlaybook(),
        repository=_FakeRepository(),
    )

    output = await use_case.execute(uuid4())

    assert output is not None
    assert len(output.actions) == 1
    assert output.actions[0].owner == "Marta"


async def test_action_outside_the_playbook_is_excluded():
    """REQ-M7-04/P3 — never an action invented outside the playbook."""
    contribution = _contribution()
    candidate = NarrationModelOutput(
        headline="We took 19 hours to reply.",
        reasons=[],
        actions=[
            NarrationActionOutput(
                text="Invented action",
                owner="Marta",
                due_date="2026-08-16",
                playbook_id=str(uuid4()),  # not in the fake playbook
            )
        ],
    )
    use_case = NarrateScoreRunUseCase(
        llm=_FakeLLM(candidate),
        score_context=_FakeScoreContext([contribution]),
        client_context=_FakeClientContext(numbers=frozenset({"19"}), names=frozenset({"Marta"})),
        playbook=_FakePlaybook(),
        repository=_FakeRepository(),
    )

    output = await use_case.execute(uuid4())

    assert output is not None
    assert output.actions == ()


async def test_headline_failing_fact_check_falls_back_to_the_deterministic_template():
    """Edge Cases — architecture/06-error-handling.md's deterministic
    fallback, `fact_check_passed = False`."""
    contribution = _contribution(finding_type="broken_response_promise", points=-39.0)
    candidate = NarrationModelOutput(
        headline="Fabricated: Xyzcorp lost 5000 points.", reasons=[], actions=[]
    )
    use_case = NarrateScoreRunUseCase(
        llm=_FakeLLM(candidate),
        score_context=_FakeScoreContext([contribution]),
        client_context=_FakeClientContext(numbers=frozenset(), names=frozenset()),
        playbook=_FakePlaybook(),
        repository=_FakeRepository(),
    )

    output = await use_case.execute(uuid4())

    assert output is not None
    assert output.fact_check_passed is False
    assert output.headline == (
        "61.0 — at_risk. Top issue: broken_response_promise (39.0 pts). "
        "See evidence trace for detail."
    )


async def test_no_findings_produces_no_narration():
    """Edge Cases — a genuinely healthy run, REQ-M8-05's own state handles
    this, not a placeholder narration."""
    use_case = NarrateScoreRunUseCase(
        llm=_FakeLLM(NarrationModelOutput(headline="", reasons=[], actions=[])),
        score_context=_FakeScoreContext([]),
        client_context=_FakeClientContext(numbers=frozenset(), names=frozenset()),
        playbook=_FakePlaybook(),
        repository=(repo := _FakeRepository()),
    )

    output = await use_case.execute(uuid4())

    assert output is None
    assert repo.persisted == []


async def test_missing_generation_config_fails_honestly_not_silently():
    """A systemic misconfiguration surfaces loudly — never silently treated
    as "nothing to narrate" (mirrors feature 007's Tone/Intent correction)."""

    class _RaisingLLM(LLMPort):
        async def generate_structured(self, prompt: str, schema: type[T]) -> T:
            raise ValueError("GENERATION_MODEL_ID is not configured")

    use_case = NarrateScoreRunUseCase(
        llm=_RaisingLLM(),
        score_context=_FakeScoreContext([_contribution()]),
        client_context=_FakeClientContext(numbers=frozenset(), names=frozenset()),
        playbook=_FakePlaybook(),
        repository=_FakeRepository(),
    )

    with pytest.raises(ValueError):
        await use_case.execute(uuid4())


async def test_swapping_ranking_order_changes_emphasis_without_narrator_resorting():
    """Acceptance Scenario 7 (REQ-M7-P2) — the use case reads
    `get_ranked_contributions`' order once and never re-sorts it; the
    fallback headline's top_issue must match whichever contribution the
    port itself calls "first," not the largest `abs(points)` value."""
    small_first = [
        _contribution("csat_deviation", -1.0),
        _contribution("broken_response_promise", -39.0),
    ]
    fabricated = NarrationModelOutput(
        headline="Fabricated: Xyzcorp lost 5000 points to Qwerty.", reasons=[], actions=[]
    )
    use_case = NarrateScoreRunUseCase(
        llm=_FakeLLM(fabricated),
        score_context=_FakeScoreContext(small_first),
        client_context=_FakeClientContext(numbers=frozenset(), names=frozenset()),
        playbook=_FakePlaybook(),
        repository=_FakeRepository(),
    )

    output = await use_case.execute(uuid4())

    assert output is not None
    assert "csat_deviation" in output.headline  # the port's first entry, not the largest

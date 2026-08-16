"""`GenerateDraftUseCase` — `LLMPort` faked (fixed structured responses, no
live Anthropic call). Covers spec.md's User Story 1 acceptance scenarios
1-3, 5 (Edge Cases: nonexistent issue/stakeholder) and User Story 2
acceptance scenarios 1-3 (Edge Cases: each of the five checks blocking
persistence), matching `test_narrate_score_run_use_case.py`'s own
fake-in-tests precedent.
"""

from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID, uuid4

import pytest

from app.experience.application.ports import (
    ClientProfileRecord,
    ClientProfileRepositoryPort,
    DraftMessageRepositoryPort,
    FindingReadPort,
    IssueReadPort,
    LedgerQueryPort,
    NarratorReadPort,
    PlaybookReadPort,
    StakeholderReadPort,
    StakeholderRecord,
)
from app.experience.application.prompts.draft_composer_v1 import DraftModelOutput
from app.experience.application.use_cases import (
    DraftCheckFailedError,
    GenerateDraftUseCase,
    IssueNotFoundError,
    StakeholderNotFoundError,
)
from app.experience.domain.entities import (
    CitedEventRecord,
    IssueEvidenceRecord,
    NarratorSummaryRecord,
)
from app.readers.application.ports import LLMPort
from app.readers.domain.entities import MessageEventInfo

T = TypeVar("T")

_ISSUE_ID = uuid4()
_STAKEHOLDER_ID = uuid4()
_REQUESTED_BY = uuid4()
_EVENT_ID = uuid4()
_PLAYBOOK_ID = uuid4()


class _FakeLLM(LLMPort):
    def __init__(self, response: DraftModelOutput) -> None:
        self._response = response

    async def generate_structured(self, prompt: str, schema: type[T]) -> T:
        return self._response  # type: ignore[return-value]


class _FakeIssueReader(IssueReadPort):
    def __init__(self, record: IssueEvidenceRecord | None) -> None:
        self._record = record

    async def get_issue_evidence(self, issue_id: UUID) -> IssueEvidenceRecord | None:
        return self._record


class _FakeStakeholderReader(StakeholderReadPort):
    def __init__(self, record: StakeholderRecord | None) -> None:
        self._record = record

    async def list_stakeholders(self) -> list[StakeholderRecord]:
        return [self._record] if self._record else []

    async def get(self, stakeholder_id: UUID) -> StakeholderRecord | None:
        return self._record


class _FakeProfile(ClientProfileRepositoryPort):
    def __init__(self, record: ClientProfileRecord | None) -> None:
        self._record = record

    async def get_current(self) -> ClientProfileRecord | None:
        return self._record


class _FakeLedger(LedgerQueryPort):
    def __init__(self, timeline: list[MessageEventInfo]) -> None:
        self._timeline = timeline

    async def baseline_vs_current(self, stakeholder_id: UUID):
        return None

    async def timeline_for_stakeholder(
        self, stakeholder_id: UUID, *, limit: int = 20
    ) -> list[MessageEventInfo]:
        return self._timeline


class _FakeNarrator(NarratorReadPort):
    def __init__(self, summary: NarratorSummaryRecord | None) -> None:
        self._summary = summary

    async def get_for_score_run(self, score_run_id: UUID):
        return None

    async def get_latest(self) -> NarratorSummaryRecord | None:
        return self._summary


class _FakePlaybook(PlaybookReadPort):
    def __init__(self, mapping: dict[UUID, str]) -> None:
        self._mapping = mapping

    async def finding_type_for_playbook(self, playbook_id: UUID) -> str | None:
        return self._mapping.get(playbook_id)


class _FakeFindingReader(FindingReadPort):
    def __init__(self, events: list[CitedEventRecord]) -> None:
        self._events = events

    async def get_finding(self, finding_id: UUID):
        return None

    async def resolve_events(self, event_ids: list[UUID]) -> list[CitedEventRecord]:
        return self._events

    async def get_commitment_comparison(self, event_id: UUID):
        return None

    async def get_usage_comparison(self, event_id: UUID):
        return None

    async def list_open_commitments(self, *, limit: int = 20):
        return []


class _FakeDraftRepository(DraftMessageRepositoryPort):
    def __init__(self) -> None:
        self.persisted: list[tuple] = []

    async def persist(self, draft, *, issue_id, stakeholder_id, requested_by_user_id) -> UUID:
        draft_id = uuid4()
        self.persisted.append((draft_id, draft, issue_id, stakeholder_id, requested_by_user_id))
        return draft_id

    async def get(self, draft_id: UUID):
        return None

    async def stamp_copied(self, draft_id: UUID) -> bool:
        return True

    async def stamp_logged_manually(self, draft_id: UUID) -> bool:
        return True


def _issue_evidence() -> IssueEvidenceRecord:
    return IssueEvidenceRecord(
        issue_id=_ISSUE_ID,
        label="Broken response promise",
        finding_types=("broken_response_promise",),
        cited_event_ids=(_EVENT_ID,),
    )


def _stakeholder() -> StakeholderRecord:
    return StakeholderRecord(
        stakeholder_id=_STAKEHOLDER_ID, name="Ana", role="Sponsor", last_seen_at=None
    )


def _profile(communication_norms: str | None = None) -> ClientProfileRecord:
    return ClientProfileRecord(
        client_name="Meridian Logistics",
        renewal_date=None,
        communication_norms=communication_norms,
    )


def _events() -> list[CitedEventRecord]:
    return [
        CitedEventRecord(
            event_id=_EVENT_ID,
            occurred_at=datetime(2026, 8, 10, tzinfo=UTC),
            quoted_text="We took 19 hours to respond to ticket #456; we promised 4.",
            structured_payload={},
        )
    ]


def _narrator_summary() -> NarratorSummaryRecord:
    return NarratorSummaryRecord(
        headline="",
        reasons=(),
        actions=(
            {
                "text": "Call Ana",
                "owner": "Marta",
                "due_date": "Thursday",
                "playbook_id": str(_PLAYBOOK_ID),
            },
        ),
    )


def _use_case(
    *,
    issue: IssueEvidenceRecord | None = ...,
    stakeholder: StakeholderRecord | None = ...,
    llm_response: DraftModelOutput | None = None,
    drafts: _FakeDraftRepository | None = None,
) -> tuple[GenerateDraftUseCase, _FakeDraftRepository]:
    issue_record = _issue_evidence() if issue is ... else issue
    stakeholder_record = _stakeholder() if stakeholder is ... else stakeholder
    repo = drafts if drafts is not None else _FakeDraftRepository()
    response = llm_response or DraftModelOutput(
        draft_text=(
            "Ana — we took 19 hours to respond to ticket #456; we promised 4. "
            "I'll call you before Thursday."
        ),
        tone_variant="direct",
    )
    use_case = GenerateDraftUseCase(
        issues=_FakeIssueReader(issue_record),
        stakeholders=_FakeStakeholderReader(stakeholder_record),
        profile=_FakeProfile(_profile()),
        ledger=_FakeLedger([]),
        narrator=_FakeNarrator(_narrator_summary()),
        playbook=_FakePlaybook({_PLAYBOOK_ID: "broken_response_promise"}),
        findings=_FakeFindingReader(_events()),
        drafts=repo,
        llm=_FakeLLM(response),
    )
    return use_case, repo


async def test_fact_check_passing_draft_is_persisted():
    """Acceptance Scenarios 1-3."""
    use_case, repo = _use_case()

    result = await use_case.execute(
        issue_id=_ISSUE_ID,
        stakeholder_id=_STAKEHOLDER_ID,
        tone_variant="direct",
        requested_by_user_id=_REQUESTED_BY,
    )

    assert result.checks_passed is True
    assert result.draft_text.startswith("Ana — we took 19 hours to respond")
    assert len(repo.persisted) == 1


async def test_nonexistent_issue_raises():
    """Edge Cases — `issue_id` doesn't resolve, `404` path."""
    use_case, _ = _use_case(issue=None)

    with pytest.raises(IssueNotFoundError):
        await use_case.execute(
            issue_id=_ISSUE_ID,
            stakeholder_id=_STAKEHOLDER_ID,
            tone_variant="direct",
            requested_by_user_id=_REQUESTED_BY,
        )


async def test_nonexistent_stakeholder_raises():
    """Edge Cases — `stakeholder_id` doesn't resolve (`/speckit-analyze`
    finding U3), `404` path."""
    use_case, _ = _use_case(stakeholder=None)

    with pytest.raises(StakeholderNotFoundError):
        await use_case.execute(
            issue_id=_ISSUE_ID,
            stakeholder_id=_STAKEHOLDER_ID,
            tone_variant="direct",
            requested_by_user_id=_REQUESTED_BY,
        )


async def test_unverified_fact_blocks_persistence():
    """User Story 2, Acceptance Scenario 1."""
    bad_response = DraftModelOutput(
        draft_text="Ana — we spoke with David about the 999-hour delay.", tone_variant="direct"
    )
    use_case, repo = _use_case(llm_response=bad_response)

    with pytest.raises(DraftCheckFailedError):
        await use_case.execute(
            issue_id=_ISSUE_ID,
            stakeholder_id=_STAKEHOLDER_ID,
            tone_variant="direct",
            requested_by_user_id=_REQUESTED_BY,
        )
    assert repo.persisted == []


async def test_invented_date_blocks_persistence():
    """User Story 2, Acceptance Scenario 2 — a date not among the issue's
    agreed actions (only "Thursday" is verified)."""
    bad_response = DraftModelOutput(
        draft_text="Ana — I'll call you before Friday.", tone_variant="direct"
    )
    use_case, repo = _use_case(llm_response=bad_response)

    with pytest.raises(DraftCheckFailedError):
        await use_case.execute(
            issue_id=_ISSUE_ID,
            stakeholder_id=_STAKEHOLDER_ID,
            tone_variant="direct",
            requested_by_user_id=_REQUESTED_BY,
        )
    assert repo.persisted == []


async def test_internal_leak_blocks_persistence():
    """User Story 2, Acceptance Scenario 3."""
    bad_response = DraftModelOutput(
        draft_text="Ana — your risk score dropped this week.", tone_variant="direct"
    )
    use_case, repo = _use_case(llm_response=bad_response)

    with pytest.raises(DraftCheckFailedError):
        await use_case.execute(
            issue_id=_ISSUE_ID,
            stakeholder_id=_STAKEHOLDER_ID,
            tone_variant="direct",
            requested_by_user_id=_REQUESTED_BY,
        )
    assert repo.persisted == []


async def test_discount_offer_blocks_persistence():
    """User Story 2, Acceptance Scenario 3 (`/speckit-analyze` finding G1)."""
    bad_response = DraftModelOutput(
        draft_text="Ana — we can offer a 10% discount this quarter.", tone_variant="direct"
    )
    use_case, repo = _use_case(llm_response=bad_response)

    with pytest.raises(DraftCheckFailedError):
        await use_case.execute(
            issue_id=_ISSUE_ID,
            stakeholder_id=_STAKEHOLDER_ID,
            tone_variant="direct",
            requested_by_user_id=_REQUESTED_BY,
        )
    assert repo.persisted == []


async def test_invented_cause_blocks_persistence():
    """`/speckit-analyze` finding U1 — REQ-M10-P3's "causes" half."""
    bad_response = DraftModelOutput(
        draft_text="Ana — the delay happened because we lost the Acme contract.",
        tone_variant="direct",
    )
    use_case, repo = _use_case(llm_response=bad_response)

    with pytest.raises(DraftCheckFailedError):
        await use_case.execute(
            issue_id=_ISSUE_ID,
            stakeholder_id=_STAKEHOLDER_ID,
            tone_variant="direct",
            requested_by_user_id=_REQUESTED_BY,
        )
    assert repo.persisted == []


async def test_agreed_actions_are_filtered_to_the_issue_finding_type():
    """`research.md` Decision 4 — an action whose playbook template applies
    to a different finding type must not be treated as this issue's own
    verified date source."""
    from app.experience.domain.services import build_verified_date_set

    other_playbook_id = uuid4()
    summary = NarratorSummaryRecord(
        headline="",
        reasons=(),
        actions=(
            {
                "text": "Call Ana",
                "owner": "Marta",
                "due_date": "Thursday",
                "playbook_id": str(_PLAYBOOK_ID),
            },
            {
                "text": "Escalate elsewhere",
                "owner": "Marta",
                "due_date": "Monday",
                "playbook_id": str(other_playbook_id),
            },
        ),
    )
    use_case, _ = _use_case()
    use_case._narrator = _FakeNarrator(summary)  # noqa: SLF001 — direct fake swap for this one test
    use_case._playbook = _FakePlaybook(
        {_PLAYBOOK_ID: "broken_response_promise", other_playbook_id: "usage_deviation"}
    )

    resolved = await use_case._resolve_agreed_actions(  # noqa: SLF001
        summary, ("broken_response_promise",)
    )

    assert [a.due_date for a in resolved] == ["Thursday"]
    dates = build_verified_date_set(resolved)
    assert "Monday" not in dates.dates

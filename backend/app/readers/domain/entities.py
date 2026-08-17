"""Reader-facing domain value objects (M5) — small frozen dataclasses each
reader's pure decision logic (`domain/services.py`) needs. `Finding`/`Issue` stay
defined once in `app.scoring.domain.entities` (`architecture/09`: "scoring owns
Finding's lifecycle") and are imported there, never redefined here.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ResponsePairInfo:
    """What `CommitmentReader`'s decision logic needs from one `response_pairs`
    row — already-computed elapsed/threshold arithmetic, no re-derivation."""

    client_event_id: UUID
    state: str
    business_hours_elapsed: float | None
    threshold_business_hours: float | None


@dataclass(frozen=True)
class CandidateTicket:
    """One embedding candidate for `RecurrenceReader` — a ticket/message's own
    identity plus the text actually embedded (its title, `research.md`'s
    Decision)."""

    event_id: UUID
    ticket_number: int
    title: str


# ---------------------------------------------------------------------------
# Tone / Intent readers + M5a validation gate — specs/007-model-findings
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MessageEventInfo:
    """One message-bearing event — the shared candidate corpus Tone and
    Intent both self-fetch from (`data-model.md`)."""

    event_id: UUID
    occurred_at: datetime
    stakeholder_id: UUID | None
    text: str


# ---------------------------------------------------------------------------
# Meeting reader — specs/011-production-hardening, User Story 6 (FR-023)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MeetingTranscriptInfo:
    """One `meeting`-type event — kept as its own type rather than reusing
    `MessageEventInfo` (a same-shaped `MessageEventRepositoryPort` row would
    also hand Tone/Intent transcripts they were never meant to classify;
    `research.md` Decision 5's "input-data change, not reader-interface
    change" applies to Absence/Relationship, not to widening the Tone/Intent
    corpus to a genuinely different content type)."""

    event_id: UUID
    occurred_at: datetime
    stakeholder_id: UUID | None
    series_id: str | None
    text: str


@dataclass(frozen=True)
class ConfirmedBaselineWindow:
    """What the Tone reader actually receives as "how this stakeholder
    normally writes" — a resolved, human-confirmed window plus the raw
    message text sampled from it, not a rolled-up scalar (`research.md`
    Decision 2)."""

    stakeholder_id: UUID
    window_start: datetime
    window_end: datetime
    sample_texts: tuple[str, ...]

    @property
    def sample_count(self) -> int:
        return len(self.sample_texts)


# `quarantine.failed_check` / `validation_check`'s existing DB enum
# (data-base/05-schema-reasoning.md) — kept as plain strings, not a Python
# Enum, matching how `Finding.status`/`reader_type` are already plain `str`
# fields elsewhere in this module.
FAILED_CHECK_VALUES = frozenset(
    {"schema_invalid", "cited_event_missing", "insufficient_evidence", "confidence_below_floor"}
)


@dataclass(frozen=True)
class FailedCheck:
    check_name: str
    expected: str
    actual: str

    def __post_init__(self) -> None:
        if self.check_name not in FAILED_CHECK_VALUES:
            raise ValueError(f"Unknown failed check: {self.check_name!r}")


@dataclass(frozen=True)
class ValidationGateResult:
    passed: bool
    failed_checks: tuple[FailedCheck, ...] = ()

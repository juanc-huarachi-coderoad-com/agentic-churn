"""Reader-facing domain value objects (M5) — small frozen dataclasses each
reader's pure decision logic (`domain/services.py`) needs. `Finding`/`Issue` stay
defined once in `app.scoring.domain.entities` (`architecture/09`: "scoring owns
Finding's lifecycle") and are imported there, never redefined here.
"""

from dataclasses import dataclass
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

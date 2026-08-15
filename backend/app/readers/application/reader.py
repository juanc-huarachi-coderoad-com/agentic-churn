"""`Reader` (M5) — `architecture/08-class-diagrams.md`'s already-named pattern.
No template-method base beyond the interface itself (unlike `Collector`) — each
reader's internal shape differs enough (a DB projection query vs. an external
embedding call) that a shared template would fight the domain rather than express
it (`research.md`'s Decision). The single-method shape mechanically enforces
REQ-M5-P1 (no reader sees another reader's output — `interpret()` has no
parameter that could carry one) and REQ-M5-P2 (no side-effect capability beyond a
return value).

Signature note (implementation-time deviation from `architecture/08`'s abstract
`interpret(events, context)`, documented here rather than silently diverging): a
generic `context: ClientProfileContext` parameter would be dead surface for four
of the five readers this feature builds — each already gets exactly the profile
data it needs via its own constructor-injected port (`ResponsePairRepositoryPort`
already resolves commitment thresholds; `RelationshipContextPort` already carries
the stakeholder list Relationship needs). `interpret()` therefore takes no
parameters; every reader fetches what it needs itself, the same dependency-
injection shape `RecomputeScoreUseCase` (feature 004) already uses.
"""

from abc import ABC, abstractmethod

from app.scoring.domain.entities import Finding


class Reader(ABC):
    reader_type: str
    reader_version: str

    @abstractmethod
    async def interpret(self) -> list[Finding]:
        """Zero or more findings, all `status = pending_validation` (REQ-M5-01/02) —
        `ValidationGate` doesn't exist until feature 007 (`research.md`'s Decision),
        so nothing downstream of this call promotes or quarantines a finding yet."""
        ...

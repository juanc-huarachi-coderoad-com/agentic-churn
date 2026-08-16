"""Ports the narrator (M7) application layer depends on — implemented by
app.narrator.adapters.*. `LLMPort` itself is imported from
`app.readers.application.ports`, not redefined here (`research.md` Decision
1 of specs/008-narrator-and-ask-agent — an already-ratified cross-module
import, per `specs/007-model-findings/research.md`'s own Decision 1).
"""

from abc import ABC, abstractmethod
from uuid import UUID

from app.narrator.domain.entities import IssueSummary, NarratorOutput, RankedContribution


class ScoreContextPort(ABC):
    @abstractmethod
    async def get_ranked_contributions(self, score_run_id: UUID) -> list[RankedContribution]:
        """`score_contributions` for this run, ordered by the scoring
        engine's own rank (most impactful first) — the Narrator reads this
        order once and never re-sorts it (REQ-M7-01, REQ-M7-P2)."""
        ...

    @abstractmethod
    async def get_top_issue(self, score_run_id: UUID) -> IssueSummary | None:
        """The single most impactful issue for this run — the deterministic
        fallback template's `top_issue` (`architecture/
        06-error-handling.md`). `None` when the run has no findings at all."""
        ...

    @abstractmethod
    async def get_score_and_band(self, score_run_id: UUID) -> tuple[float, str] | None:
        """`(score, band)` for the fallback template's own placeholders."""
        ...


class ClientContextPort(ABC):
    @abstractmethod
    async def build_verified_facts(
        self, cited_event_ids: list[UUID]
    ) -> tuple[frozenset[str], frozenset[str]]:
        """`(numbers, names)` — the real numbers and names actually present
        in these cited events (stakeholder names, ticket numbers, hour
        counts) — the concrete material `VerifiedFactSet` is built from."""
        ...


class PlaybookPort(ABC):
    @abstractmethod
    async def list_active(self, finding_type: str) -> list["PlaybookTemplate"]:
        """`playbook_actions WHERE is_active AND applies_to_finding_type =
        :finding_type` — the fixed menu the Narrator personalizes from,
        never invents outside of (REQ-M7-04, REQ-M7-P3)."""
        ...


class PlaybookTemplate:
    __slots__ = ("id", "template_text", "default_owner_role", "default_sla_days")

    def __init__(
        self, id: UUID, template_text: str, default_owner_role: str, default_sla_days: int
    ) -> None:
        self.id = id
        self.template_text = template_text
        self.default_owner_role = default_owner_role
        self.default_sla_days = default_sla_days


class NarratorOutputRepositoryPort(ABC):
    @abstractmethod
    async def persist(self, output: NarratorOutput, score_run_id: UUID) -> None:
        """One `INSERT` into `narrator_outputs`, `UNIQUE(score_run_id)`
        already enforcing "exactly one row per run" at the DB level."""
        ...

"""Ports the context application layer depends on — implemented by
app.context.adapters.*. Application depends on these, never on a concrete adapter
(constitution P8), enforced mechanically by `.importlinter`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.context.domain.entities import DampingWeight, FindingPatternComponents
from app.context.domain.profile_schema import ClientProfileInput


@dataclass(frozen=True)
class StakeholderSummary:
    name: str
    role: str | None
    influence: str
    signs_renewal: bool


@dataclass(frozen=True)
class ProductAreaSummary:
    key: str
    criticality: str


@dataclass(frozen=True)
class CommitmentSummary:
    type: str
    threshold_business_hours: float | None


@dataclass(frozen=True)
class ProfileVersionSummary:
    version_number: int
    client_name: str
    renewal_date: date
    contract_value_band: str
    stakeholders: list[StakeholderSummary]
    product_areas: list[ProductAreaSummary]
    commitments: list[CommitmentSummary]
    # specs/011-production-hardening, User Story 5 (FR-017) — a real gap found
    # while wiring the editor UI: this summary never carried these two fields,
    # even though the client_profile_versions columns behind them
    # (communication_norms, exclusions) have existed since feature 003. Without
    # them, the editor could never show — or safely round-trip — a client's
    # current exclusions/communication norms.
    exclusions: list[str]
    communication_norms: str | None


class ClientProfileRepositoryPort(ABC):
    @abstractmethod
    async def insert_new_version(
        self, profile: ClientProfileInput, *, authored_by_user_id: UUID
    ) -> ProfileVersionSummary:
        """Inserts a new `client_profile_versions` row (+ stakeholders/product_areas/
        commitments/profile_history_entries), flips the prior current version's
        `is_current` to false in the same transaction (REQ-M3-02)."""
        ...

    @abstractmethod
    async def get_current(self) -> ProfileVersionSummary | None: ...


# ---------------------------------------------------------------------------
# M4 · Feedback memory (`specs/010-feedback-memory/data-model.md`)
# ---------------------------------------------------------------------------


class FeedbackFindingReadPort(ABC):
    @abstractmethod
    async def get_pattern_components(
        self, finding_id: UUID
    ) -> FindingPatternComponents | None:
        """`None` if `finding_id` doesn't exist or isn't `validated` — mirrors
        `SqlAlchemyFindingReader.get_finding`'s existing validated-only filter
        precedent (`app.experience.adapters.sqlalchemy_repository`)."""
        ...


class IssueTopFindingReadPort(ABC):
    @abstractmethod
    async def get_top_finding_id(self, issue_id: UUID) -> UUID | None:
        """`rank_within_issue = 1` for the given issue; `None` if the issue
        doesn't exist or has no mapped findings."""
        ...


class FeedbackVerdictRepositoryPort(ABC):
    @abstractmethod
    async def get_damping(self, pattern_signature: str) -> DampingWeight:
        """A zeroed, `weight=1.0` default if no row exists yet — never
        `None` (FR-008's upsert semantics live at the write, not the read)."""
        ...

    @abstractmethod
    async def record(
        self,
        *,
        finding_id: UUID | None,
        issue_id: UUID | None,
        verdict: str,
        submitted_by_user_id: UUID,
        updated: DampingWeight,
    ) -> None:
        """One transaction: append to `feedback_verdicts`, upsert
        `damping_weights`."""
        ...

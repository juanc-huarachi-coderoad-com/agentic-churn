"""Ports the scoring application layer depends on — implemented by
app.scoring.adapters.*. Application depends on these, never on a concrete adapter
(constitution P8, Dependency Inversion), enforced mechanically by `.importlinter`.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.scoring.domain.entities import (
    Finding,
    FindingLifecycle,
    ScoreContribution,
    ScoreRun,
)

# ---------------------------------------------------------------------------
# Findings + issue groupings (FindingRepositoryPort — architecture/09)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FindingTypeConfig:
    base_points: float
    half_life_days: float | None


class FindingRepositoryPort(ABC):
    @abstractmethod
    async def list_validated(self) -> list[Finding]: ...

    @abstractmethod
    async def get_finding_type_config(self, finding_type: str) -> FindingTypeConfig: ...

    @abstractmethod
    async def get_finding_type_config_version(self) -> str: ...

    @abstractmethod
    async def resolve_lifecycle(self, finding: Finding) -> FindingLifecycle: ...

    @abstractmethod
    async def list_issue_memberships(self) -> dict[UUID, list[UUID]]:
        """`issue_id -> [finding_id, ...]`, from `finding_issue_map` — the grouping
        only, never `rank_within_issue` (that's `IssueGrouper`'s own output, not an
        input read back)."""
        ...

    @abstractmethod
    async def update_finding_state(self, finding_id: UUID, state: str) -> None: ...

    @abstractmethod
    async def upsert_ranks(self, ranks: dict[tuple[UUID, UUID], int]) -> None:
        """`(finding_id, issue_id) -> rank_within_issue`, written by `IssueGrouper`
        — keyed by the composite `finding_issue_map` primary key, not `finding_id`
        alone, since a finding could in principle belong to more than one issue."""
        ...


# ---------------------------------------------------------------------------
# score_runs / score_contributions / band_history (ScoreRunRepositoryPort)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BandHistoryRecord:
    band: str
    consecutive_runs_in_band: int


class ScoreRunRepositoryPort(ABC):
    @abstractmethod
    async def get_latest_band_history(self) -> BandHistoryRecord | None: ...

    @abstractmethod
    async def get_latest_score_run(self) -> ScoreRun | None:
        """Used only by the source-degraded freeze path (T026) to know what value
        to copy forward — never read by the normal compute path (REQ-M6-20,
        REQ-M6-P2: the previous score is never an input to a fresh computation)."""
        ...

    @abstractmethod
    async def persist_run(
        self, run: ScoreRun, contributions: list[ScoreContribution]
    ) -> None: ...

    @abstractmethod
    async def persist_band_history(
        self, *, score_run_id: UUID, band: str, consecutive_runs_in_band: int
    ) -> None: ...


# ---------------------------------------------------------------------------
# Client profile multipliers (ClientProfileMultipliersPort)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProfileMultiplierContext:
    profile_version_id: UUID
    stakeholder_multipliers: dict[UUID, float]
    product_area_multipliers: dict[UUID, float]
    contract_value_band: str
    renewal_date: date


class ClientProfileMultipliersPort(ABC):
    @abstractmethod
    async def get_current(self) -> ProfileMultiplierContext: ...


# ---------------------------------------------------------------------------
# Damping (DampingRepositoryPort)
# ---------------------------------------------------------------------------


class DampingRepositoryPort(ABC):
    @abstractmethod
    async def get_weight(self, pattern_signature: str) -> float:
        """1.0 (undamped) if no row exists yet for this pattern (REQ-M6-05,
        REQ-M6-CAL-03a)."""
        ...


# ---------------------------------------------------------------------------
# Coverage / source-degraded check (CoverageCheckPort)
# ---------------------------------------------------------------------------


class CoverageCheckPort(ABC):
    @abstractmethod
    async def is_degraded(self) -> bool:
        """True if the most recent coverage report shows `sources_read <
        sources_expected` (REQ-M6-26, REQ-NFR-32)."""
        ...


# ---------------------------------------------------------------------------
# finding_type_config writes (specs/011-production-hardening, User Story 4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FindingTypeConfigChangeResult:
    change_id: UUID
    new_config_version: str
    changed_at: datetime


class FindingTypeConfigWritePort(ABC):
    @abstractmethod
    async def update_base_points(
        self,
        finding_type: str,
        new_base_points: float,
        changed_by_user_id: UUID,
    ) -> FindingTypeConfigChangeResult:
        """Updates `finding_type_config.base_points`, bumps the shared
        `finding_type_config.version` string (every score run computed after
        this point carries a visibly different `finding_type_config_version`
        than every run before it — REQ-NFR-08/FR-015), and inserts one audit
        row into `finding_type_config_changes` (FR-014) — all in one
        transaction. Raises `FindingTypeNotFoundError` if `finding_type`
        doesn't exist in `finding_type_config`."""
        ...


class FindingTypeNotFoundError(Exception):
    """`finding_type` doesn't exist in `finding_type_config` — a `404`, not a
    silently-inserted row (`contracts/weight-recalibration.md`)."""


__all__ = [
    "BandHistoryRecord",
    "ClientProfileMultipliersPort",
    "CoverageCheckPort",
    "DampingRepositoryPort",
    "Finding",
    "FindingLifecycle",
    "FindingRepositoryPort",
    "FindingTypeConfig",
    "FindingTypeConfigChangeResult",
    "FindingTypeConfigWritePort",
    "FindingTypeNotFoundError",
    "ProfileMultiplierContext",
    "ScoreContribution",
    "ScoreRun",
    "ScoreRunRepositoryPort",
]

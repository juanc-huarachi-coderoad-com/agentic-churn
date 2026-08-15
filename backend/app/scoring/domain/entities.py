"""Domain entities for M6 (scoring) — `Finding`, `Issue`, `ScoreRun`,
`ScoreContribution` — defined once, here, per `architecture/09-clean-architecture-
and-patterns.md`'s pattern catalog: `scoring.domain` owns `Finding`'s lifecycle, since
the scoring engine is what sets `state` (`data-base/05-schema-reasoning.md`'s own
schema comment). Future modules (`readers`) re-export these, never redefine them.

Pure dataclasses, no I/O, no framework imports — mirrors each table's own columns
(`data-base/05-schema-reasoning.md`, `data-base/06-schema-scoring.md`), no
restatement of field meaning here.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

# The one seeded finding_type matching REQ-M6-13's positive-signal examples
# (milestones met, successful reviews) — `spec.md`'s Assumptions: no `is_positive`/
# sign column exists on `findings` or `finding_type_config`, so this classification
# is a small, explicit lookup (matching `data-base/04-schema-context.md`'s "small
# config table maintained separately from client data" pattern for multiplier
# categories), not inferred from a database column.
POSITIVE_FINDING_TYPES = frozenset({"commitment_met"})


def is_positive_finding_type(finding_type: str) -> bool:
    return finding_type in POSITIVE_FINDING_TYPES


@dataclass(frozen=True)
class Finding:
    id: UUID
    reader_type: str
    reader_version: str
    finding_type: str
    magnitude: float
    confidence: float
    cited_event_ids: tuple[UUID, ...]
    stakeholder_id: UUID | None
    product_area_id: UUID | None
    status: str
    state: str | None
    is_positive: bool


@dataclass(frozen=True)
class Issue:
    id: UUID
    label: str
    cluster_method: str


@dataclass(frozen=True)
class ScoreRun:
    id: UUID
    trigger: str
    profile_version_id: UUID
    finding_type_config_version: str
    total_negative_points: float
    total_positive_points: float
    positive_points_applied: float
    total_points: float
    score: float
    band: str
    raw_band: str
    stakes: float | None
    source_degraded: bool
    is_frozen: bool
    computed_at: datetime


@dataclass(frozen=True)
class FindingLifecycle:
    """What `AgeingCalculator` needs to compute `recency` for one finding —
    resolved by joining the finding's `cited_event_ids` back to `response_pairs`
    for the two commitment-lifecycle finding types; every other type is always
    `open` with nothing else to resolve (`research.md`'s Decision)."""

    state: str
    business_hours_elapsed: float | None
    threshold_business_hours: float | None
    resolved_at: datetime | None


@dataclass(frozen=True)
class ScoreContribution:
    score_run_id: UUID
    finding_id: UUID
    issue_id: UUID | None
    base: float
    influence: float
    criticality: float
    confidence: float
    magnitude: float
    recency: float
    damping: float
    rank_within_issue_factor: float
    points_contributed: float
    is_positive: bool

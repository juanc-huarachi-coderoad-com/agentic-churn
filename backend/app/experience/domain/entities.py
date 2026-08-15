"""Domain value objects for the dashboard/evidence-trace read layer (M8) —
`app.experience.domain.services`'s pure functions consume/produce these, no
I/O. `data-model.md`'s own list.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

DashboardStateKind = Literal[
    "no_profile",
    "source_down",
    "unresolved_person",
    "catching_up",
    "learning",
    "healthy_quiet",
    "normal",
]

PulseSeverity = Literal["info", "watch", "at_risk"]


@dataclass(frozen=True)
class DashboardState:
    """`research.md`'s seven-value precedence result, plus whichever
    interpolated values that state's exact `base/...md` §11.5 copy needs —
    never a bare string the frontend has to parse."""

    kind: DashboardStateKind
    source_name: str | None = None
    last_read_at: datetime | None = None
    minutes_behind: int | None = None
    unresolved_domain: str | None = None
    unresolved_count: int | None = None
    connected_signal_types: int | None = None
    minutes_since_last_check: int | None = None


@dataclass(frozen=True)
class EvidenceComparison:
    """One finding type's baseline-vs-current shape — `data-model.md`'s
    dispatch table's output."""

    baseline_label: str
    current_label: str
    what_changed: tuple[str, ...]


@dataclass(frozen=True)
class ArithmeticClause:
    """One plain-language sentence fragment describing a single non-neutral
    `score_contributions` factor — `research.md`'s "skip neutral factors"
    Decision."""

    text: str


# ---------------------------------------------------------------------------
# Data-transfer shapes the evidence-dispatch pure functions
# (app.experience.domain.services) consume — defined here, not in
# application/ports.py, so domain never imports application (constitution P8;
# the same fix feature 004 already made once for this exact violation shape).
# `application.ports` imports these from here, not the other way around.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ContributionRecord:
    id: UUID
    finding_id: UUID
    finding_type: str
    points_contributed: float
    is_positive: bool
    base: float
    influence: float
    criticality: float
    confidence: float
    magnitude: float
    recency: float
    damping: float
    rank_within_issue_factor: float


@dataclass(frozen=True)
class CitedEventRecord:
    event_id: UUID
    occurred_at: datetime
    quoted_text: str | None
    structured_payload: dict[str, object]


@dataclass(frozen=True)
class CommitmentComparisonRecord:
    business_hours_elapsed: float
    threshold_business_hours: float
    state: str


@dataclass(frozen=True)
class UsageComparisonRecord:
    metric: str
    historical_mean: float
    latest_value: float

"""Domain value objects for the dashboard/evidence-trace read layer (M8) —
`app.experience.domain.services`'s pure functions consume/produce these, no
I/O. `data-model.md`'s own list.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from uuid import UUID

from app.narrator.domain.entities import FactCheckResult

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
    issue_id: UUID | None = None
    """Added for the Ask agent's "write to X about this" handoff
    (specs/008-narrator-and-ask-agent) — `component_props.issue_id`. An
    additive field, ignored by every existing consumer (contribution_bars
    never renders it) — `score_contributions.issue_id` already exists in
    the schema, this is the first read path to surface it."""


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


# ---------------------------------------------------------------------------
# Ask agent (M9) — specs/008-narrator-and-ask-agent
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CommitmentStatusRecord:
    """One `response_pairs` row — what "what did we promise them?" reads,
    distinct from `CommitmentComparisonRecord` above (that one compares a
    single cited event's own elapsed/threshold; this one lists every open
    or recently-resolved promise for the timeline view)."""

    event_id: UUID
    occurred_at: datetime
    quoted_text: str | None
    state: str
    business_hours_elapsed: float | None
    threshold_business_hours: float | None


@dataclass(frozen=True)
class NarratorSummaryRecord:
    """`narrator_outputs`' headline/reasons/actions for one score run —
    the same row `DashboardResponse.narrator` renders (`contracts/
    dashboard.md`) and "what should we do?" reads its `actions` from."""

    headline: str
    reasons: tuple[dict[str, object], ...]
    actions: tuple[dict[str, object], ...]


# ---------------------------------------------------------------------------
# Draft composer (M10) — specs/009-draft-composer. `VerifiedFactSet`/
# `FactCheckResult` are NOT redefined here — imported from
# `app.narrator.domain.entities` (research.md Decision 2).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IssueEvidenceRecord:
    """The requested issue's own aggregated evidence — `IssueReadPort.
    get_issue_evidence`'s return shape. Any issue with cited evidence, not
    only the top-ranked one (Clarifications, 2026-08-16)."""

    issue_id: UUID
    label: str
    finding_types: tuple[str, ...]
    cited_event_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class AgreedAction:
    """One of the latest run's already-narrated actions, filtered to the
    requested issue's own finding types (research.md Decision 4) — the
    source of every date `verify_dates` accepts."""

    text: str
    owner: str
    due_date: str
    finding_type: str


@dataclass(frozen=True)
class VerifiedDateSet:
    """Every date/day-name token legitimately present in the issue's
    `AgreedAction`s and thread history — built once, before generation."""

    dates: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class DateCheckResult:
    passed: bool
    unverified_dates: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class CauseCheckResult:
    """`verify_no_invented_cause`'s outcome (research.md Decision 6,
    `/speckit-analyze` finding U1) — every causal clause's numbers/names
    must already be in the same `VerifiedFactSet` `verify_facts` uses."""

    passed: bool
    unverified_causal_clauses: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class LeakCheckResult:
    """One candidate draft's internal-leak-check outcome (denylist +
    other-client-name check)."""

    passed: bool
    leaked_terms: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ConcessionCheckResult:
    """`verify_no_concession`'s outcome (research.md Decision 6,
    `/speckit-analyze` finding G1) — closed denylist match."""

    passed: bool
    matched_terms: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class DraftCheckResult:
    """The composed result of all five checks — `passed` is `True` only if
    all five are (REQ-M10-07)."""

    passed: bool
    fact_check: FactCheckResult
    date_check: DateCheckResult
    cause_check: CauseCheckResult
    leak_check: LeakCheckResult
    concession_check: ConcessionCheckResult


@dataclass(frozen=True)
class GeneratedDraft:
    """The use case's pre-persistence result."""

    draft_text: str
    tone_variant: str
    evidence_event_ids: tuple[UUID, ...]
    check_result: DraftCheckResult

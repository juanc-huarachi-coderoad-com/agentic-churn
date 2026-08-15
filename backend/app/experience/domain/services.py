"""Pure domain logic for the dashboard/evidence-trace read layer (M8) — no
I/O, unit-testable with plain values. Mirrors `app.scoring.domain.services`'s
own shape: adapters fetch raw rows, these functions decide what to show
(`research.md`'s Decisions).
"""

from datetime import datetime

from app.experience.domain.entities import (
    ArithmeticClause,
    CitedEventRecord,
    CommitmentComparisonRecord,
    ContributionRecord,
    DashboardState,
    EvidenceComparison,
    PulseSeverity,
    UsageComparisonRecord,
)

# ---------------------------------------------------------------------------
# Dashboard state precedence (REQ-M8-07)
# ---------------------------------------------------------------------------

_UNRESOLVED_PERSON_THRESHOLD = 3
_SIGNAL_TYPE_COUNT = 6


def resolve_dashboard_state(
    *,
    has_profile: bool,
    disconnected_source_name: str | None,
    disconnected_source_last_read_at: datetime | None,
    unresolved_domain: str | None,
    unresolved_count: int,
    degraded: bool,
    minutes_behind: int | None,
    connected_signal_types: int,
    band: str | None,
    contribution_count: int,
    minutes_since_last_check: int,
) -> DashboardState:
    """The fixed precedence `research.md`'s Decision defines — highest first:
    `no_profile` > `source_down` > `unresolved_person` > `catching_up` >
    `learning` > `healthy_quiet` > `normal`. A concrete gap is always
    surfaced over an ambient one (spec.md's Edge Cases)."""
    if not has_profile:
        return DashboardState(kind="no_profile")

    if disconnected_source_name is not None:
        return DashboardState(
            kind="source_down",
            source_name=disconnected_source_name,
            last_read_at=disconnected_source_last_read_at,
        )

    if unresolved_count >= _UNRESOLVED_PERSON_THRESHOLD:
        return DashboardState(
            kind="unresolved_person",
            unresolved_domain=unresolved_domain,
            unresolved_count=unresolved_count,
        )

    if degraded:
        return DashboardState(kind="catching_up", minutes_behind=minutes_behind)

    if connected_signal_types < _SIGNAL_TYPE_COUNT:
        return DashboardState(
            kind="learning", connected_signal_types=connected_signal_types
        )

    if band == "healthy" and contribution_count == 0:
        return DashboardState(
            kind="healthy_quiet", minutes_since_last_check=minutes_since_last_check
        )

    return DashboardState(kind="normal")


def render_state_message(state: DashboardState) -> str | None:
    """`base/...md` §11.5's exact copy per state — `None` for `no_profile`/
    `normal`, which carry no banner message."""
    if state.kind == "source_down":
        when = (
            state.last_read_at.strftime("%a %H:%M")
            if state.last_read_at is not None
            else "yet"
        )
        preposition = "since" if state.last_read_at is not None else ""
        parts = [p for p in (preposition, when) if p]
        return f"{state.source_name} hasn't been read {' '.join(parts)} — reconnect."

    if state.kind == "unresolved_person":
        return (
            f"Someone at {state.unresolved_domain} has written "
            f"{state.unresolved_count} times and isn't in the profile. Who is this?"
        )

    if state.kind == "catching_up":
        return f"Partial data — {state.minutes_behind} minutes behind."

    if state.kind == "learning":
        return f"Still learning — {state.connected_signal_types} of 6 signal types available."

    if state.kind == "healthy_quiet":
        return (
            f"Nothing needs you today. Last checked "
            f"{state.minutes_since_last_check} minutes ago."
        )

    return None


# ---------------------------------------------------------------------------
# Pulse timeline severity (REQ-M8-02, reuses FR-012's red/amber rule verbatim)
# ---------------------------------------------------------------------------

_AT_RISK_FINDING_TYPES = frozenset({"broken_response_promise", "contact_absence"})


def pulse_severity(*, finding_type: str, is_positive: bool) -> PulseSeverity:
    """`info` for a positive finding; `at_risk` only for the two finding types
    FR-012/REQ-M8-10 already name as red-color triggers (a broken promise, a
    disengaged sponsor); `watch` for every other negative finding — the same
    rule this feature's contribution-bar/score-block styling must also apply
    (never a naive "negative = red")."""
    if is_positive:
        return "info"
    if finding_type in _AT_RISK_FINDING_TYPES:
        return "at_risk"
    return "watch"


# ---------------------------------------------------------------------------
# Evidence dispatch table (REQ-M8-08, data-model.md's table) — one pure
# function per finding_type, plus a fallback for any type outside the five
# (`research.md`'s Decision, `/speckit-analyze` finding CV1).
# ---------------------------------------------------------------------------


def evaluate_commitment_evidence(comparison: CommitmentComparisonRecord) -> EvidenceComparison:
    what_changed = []
    if comparison.business_hours_elapsed > comparison.threshold_business_hours:
        what_changed.append("response time exceeded the promised threshold")
    if comparison.state == "open_overdue":
        what_changed.append("the ticket has not yet resolved")
    current = f"{comparison.business_hours_elapsed:g} business hours elapsed"
    if comparison.state == "open_overdue":
        current += ", still open"
    return EvidenceComparison(
        baseline_label=(
            f"responds within {comparison.threshold_business_hours:g} "
            "promised business hours"
        ),
        current_label=current,
        what_changed=tuple(what_changed),
    )


def evaluate_usage_evidence(comparison: UsageComparisonRecord) -> EvidenceComparison:
    direction = "down" if comparison.latest_value < comparison.historical_mean else "up"
    return EvidenceComparison(
        baseline_label=(
            f"{comparison.metric} typically averages "
            f"{comparison.historical_mean:.1f}% week over week"
        ),
        current_label=f"{comparison.metric} moved {comparison.latest_value:+.1f}% this week",
        what_changed=(f"usage moved {direction} sharply from its own history",),
    )


def evaluate_absence_evidence(event: CitedEventRecord) -> EvidenceComparison:
    cadence = event.structured_payload.get("cadence", "the expected cadence")
    return EvidenceComparison(
        baseline_label=f"expected contact every {cadence}",
        current_label="no contact within that window",
        what_changed=("missed the expected contact cadence",),
    )


def evaluate_relationship_evidence(event: CitedEventRecord) -> EvidenceComparison:
    return EvidenceComparison(
        baseline_label="active within the last 4 weeks",
        current_label=f"last active {event.occurred_at.date().isoformat()}",
        what_changed=("stakeholder went quiet",),
    )


def evaluate_recurrence_evidence(*, cited_event_count: int) -> EvidenceComparison:
    return EvidenceComparison(
        baseline_label="a single reported issue",
        current_label=f"{cited_event_count} related occurrences",
        what_changed=("the same underlying problem recurred",),
    )


_GENERIC_EVIDENCE_TEXT = (
    "a detailed comparison for this finding type isn't available "
    "until its owning reader ships"
)


def evaluate_generic_evidence() -> EvidenceComparison:
    """The fallback for any `finding_type` outside the five above — real
    today for `escalation_language`/`tone_deterioration`/`csat_deviation`
    (feature 007's future readers). Honestly absent, never a fabricated
    per-type detail for a type this feature doesn't yet understand
    (`research.md`'s Decision, `/speckit-analyze` finding CV1)."""
    return EvidenceComparison(
        baseline_label=_GENERIC_EVIDENCE_TEXT,
        current_label=_GENERIC_EVIDENCE_TEXT,
        what_changed=(),
    )


# ---------------------------------------------------------------------------
# Arithmetic-in-words (REQ-M8-08, `base/...md` §11.4) — deterministic
# template formatting, never a model call (constitution P2; `research.md`'s
# Decision). Finding-type-agnostic — unaffected by the fallback above.
# ---------------------------------------------------------------------------

_NEUTRAL = 1.0
_NEUTRAL_EPSILON = 0.0005

_ARITHMETIC_FACTOR_LABELS: tuple[tuple[str, str], ...] = (
    ("influence", "stakeholder influence"),
    ("criticality", "product area criticality"),
    ("confidence", "reader confidence"),
    ("magnitude", "finding magnitude"),
    ("recency", "recency"),
    ("damping", "prior feedback"),
    ("rank_within_issue_factor", "issue ranking"),
)


def _is_neutral(value: float) -> bool:
    return abs(value - _NEUTRAL) < _NEUTRAL_EPSILON


def format_arithmetic(contribution: ContributionRecord) -> tuple[ArithmeticClause, ...]:
    """One clause per non-neutral `score_contributions` factor, skipping
    neutral (1.000) ones (`research.md`'s "skip neutral factors" Decision)."""
    clauses = [
        ArithmeticClause(text=f"Base {contribution.base:g} points for {contribution.finding_type}")
    ]
    for field_name, label in _ARITHMETIC_FACTOR_LABELS:
        value: float = getattr(contribution, field_name)
        if _is_neutral(value):
            continue
        pct = abs(value - _NEUTRAL) * 100
        verb = "increased" if value > _NEUTRAL else "reduced"
        clauses.append(ArithmeticClause(text=f"{verb} {pct:.0f}% for {label}"))
    clauses.append(
        ArithmeticClause(text=f"{contribution.points_contributed:g} points total")
    )
    return tuple(clauses)

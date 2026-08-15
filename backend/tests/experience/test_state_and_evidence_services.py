"""REQ-M8-07 — `resolve_dashboard_state()`'s precedence ordering, all seven
states, plain values, no DB. Evidence-dispatch tests (T025, US2) extend this
file.
"""

import uuid
from datetime import UTC, datetime

from app.experience.domain.entities import (
    CitedEventRecord,
    CommitmentComparisonRecord,
    ContributionRecord,
    UsageComparisonRecord,
)
from app.experience.domain.services import (
    evaluate_absence_evidence,
    evaluate_commitment_evidence,
    evaluate_generic_evidence,
    evaluate_recurrence_evidence,
    evaluate_relationship_evidence,
    evaluate_usage_evidence,
    format_arithmetic,
    pulse_severity,
    render_state_message,
    resolve_dashboard_state,
)

_BASE_KWARGS = {
    "has_profile": True,
    "disconnected_source_name": None,
    "disconnected_source_last_read_at": None,
    "unresolved_domain": None,
    "unresolved_count": 0,
    "degraded": False,
    "minutes_behind": None,
    "connected_signal_types": 6,
    "band": "healthy",
    "contribution_count": 1,
    "minutes_since_last_check": 4,
}


def _state(**overrides):
    kwargs = {**_BASE_KWARGS, **overrides}
    return resolve_dashboard_state(**kwargs)


def test_no_profile_outranks_everything():
    state = _state(has_profile=False, disconnected_source_name="Email")
    assert state.kind == "no_profile"


def test_source_down_outranks_unresolved_person():
    state = _state(
        disconnected_source_name="Email",
        disconnected_source_last_read_at=datetime(2026, 8, 11, 9, 14, tzinfo=UTC),
        unresolved_domain="meridian.com",
        unresolved_count=5,
    )
    assert state.kind == "source_down"
    assert state.source_name == "Email"


def test_unresolved_person_outranks_catching_up():
    state = _state(unresolved_domain="meridian.com", unresolved_count=3, degraded=True)
    assert state.kind == "unresolved_person"
    assert state.unresolved_count == 3


def test_unresolved_person_requires_at_least_three():
    state = _state(unresolved_domain="meridian.com", unresolved_count=2)
    assert state.kind != "unresolved_person"


def test_catching_up_outranks_learning():
    state = _state(degraded=True, minutes_behind=40, connected_signal_types=3)
    assert state.kind == "catching_up"
    assert state.minutes_behind == 40


def test_learning_outranks_healthy_quiet():
    state = _state(connected_signal_types=3, band="healthy", contribution_count=0)
    assert state.kind == "learning"
    assert state.connected_signal_types == 3


def test_healthy_quiet_requires_zero_contributions():
    state = _state(band="healthy", contribution_count=0)
    assert state.kind == "healthy_quiet"


def test_healthy_band_with_contributions_is_normal_not_healthy_quiet():
    state = _state(band="healthy", contribution_count=1)
    assert state.kind == "normal"


def test_at_risk_band_is_normal():
    state = _state(band="at_risk", contribution_count=3)
    assert state.kind == "normal"


def test_state_messages_match_the_required_copy():
    assert render_state_message(_state(band="healthy", contribution_count=0)) == (
        "Nothing needs you today. Last checked 4 minutes ago."
    )
    learning = _state(connected_signal_types=3, band="healthy", contribution_count=0)
    assert render_state_message(learning) == "Still learning — 3 of 6 signal types available."
    catching_up = _state(degraded=True, minutes_behind=40, connected_signal_types=3)
    assert render_state_message(catching_up) == "Partial data — 40 minutes behind."
    unresolved = _state(unresolved_domain="meridian.com", unresolved_count=3)
    assert render_state_message(unresolved) == (
        "Someone at meridian.com has written 3 times and isn't in the profile. Who is this?"
    )
    assert render_state_message(_state(band="at_risk", contribution_count=1)) is None
    assert render_state_message(_state(has_profile=False)) is None


def test_pulse_severity_reuses_fr_012s_red_amber_rule():
    assert pulse_severity(finding_type="commitment_met", is_positive=True) == "info"
    assert pulse_severity(finding_type="broken_response_promise", is_positive=False) == "at_risk"
    assert pulse_severity(finding_type="contact_absence", is_positive=False) == "at_risk"
    assert pulse_severity(finding_type="usage_deviation", is_positive=False) == "watch"
    assert pulse_severity(finding_type="relationship_change", is_positive=False) == "watch"
    assert pulse_severity(finding_type="recurring_issue", is_positive=False) == "watch"


def test_commitment_evidence_matches_the_worked_example():
    """data-model.md's ticket #456 worked example: 50h elapsed vs 4h promised,
    still open."""
    comparison = CommitmentComparisonRecord(
        business_hours_elapsed=50.0, threshold_business_hours=4.0, state="open_overdue"
    )
    result = evaluate_commitment_evidence(comparison)
    assert result.baseline_label == "responds within 4 promised business hours"
    assert result.current_label == "50 business hours elapsed, still open"
    assert result.what_changed == (
        "response time exceeded the promised threshold",
        "the ticket has not yet resolved",
    )


def test_commitment_evidence_resolved_within_threshold_has_no_what_changed():
    comparison = CommitmentComparisonRecord(
        business_hours_elapsed=2.0, threshold_business_hours=4.0, state="resolved"
    )
    result = evaluate_commitment_evidence(comparison)
    assert result.what_changed == ()


def test_usage_evidence_matches_the_worked_shape():
    comparison = UsageComparisonRecord(
        metric="weekly_active_usage", historical_mean=-0.6, latest_value=-22.0
    )
    result = evaluate_usage_evidence(comparison)
    assert "typically averages -0.6%" in result.baseline_label
    assert "-22.0%" in result.current_label
    assert result.what_changed == ("usage moved down sharply from its own history",)


def test_absence_evidence_reads_the_events_own_cadence():
    event = CitedEventRecord(
        event_id=uuid.uuid4(),
        occurred_at=datetime(2026, 8, 14, 19, 30, tzinfo=UTC),
        quoted_text=None,
        structured_payload={"cadence": "weekly"},
    )
    result = evaluate_absence_evidence(event)
    assert result.baseline_label == "expected contact every weekly"
    assert result.what_changed == ("missed the expected contact cadence",)


def test_relationship_evidence_cites_the_events_occurred_at():
    event = CitedEventRecord(
        event_id=uuid.uuid4(),
        occurred_at=datetime(2026, 7, 1, 15, 0, tzinfo=UTC),
        quoted_text=None,
        structured_payload={},
    )
    result = evaluate_relationship_evidence(event)
    assert result.baseline_label == "active within the last 4 weeks"
    assert "2026-07-01" in result.current_label


def test_recurrence_evidence_counts_cited_events():
    result = evaluate_recurrence_evidence(cited_event_count=2)
    assert result.current_label == "2 related occurrences"
    assert result.baseline_label == "a single reported issue"


def test_generic_evidence_fallback_is_honest_not_fabricated():
    """`/speckit-analyze` finding CV1 — a finding_type outside the five-entry
    dispatch (e.g. escalation_language, real in this deployment's own seed
    data) never crashes and never invents a per-type detail."""
    result = evaluate_generic_evidence()
    assert "isn't available" in result.baseline_label
    assert result.what_changed == ()


def test_format_arithmetic_matches_the_worked_example():
    """data-model.md's ticket #456 contribution: base 20, criticality 1.5,
    recency 1.3, everything else neutral — 39.0 points total."""
    contribution = ContributionRecord(
        id=uuid.uuid4(),
        finding_id=uuid.uuid4(),
        finding_type="broken_response_promise",
        points_contributed=39.0,
        is_positive=False,
        base=20.0,
        influence=1.0,
        criticality=1.5,
        confidence=1.0,
        magnitude=1.0,
        recency=1.3,
        damping=1.0,
        rank_within_issue_factor=1.0,
    )
    clauses = [c.text for c in format_arithmetic(contribution)]
    assert clauses == [
        "Base 20 points for broken_response_promise",
        "increased 50% for product area criticality",
        "increased 30% for recency",
        "39 points total",
    ]


def test_format_arithmetic_skips_every_neutral_factor():
    contribution = ContributionRecord(
        id=uuid.uuid4(),
        finding_id=uuid.uuid4(),
        finding_type="commitment_met",
        points_contributed=4.0,
        is_positive=True,
        base=10.0,
        influence=1.0,
        criticality=1.0,
        confidence=1.0,
        magnitude=0.4,
        recency=1.0,
        damping=1.0,
        rank_within_issue_factor=1.0,
    )
    clauses = [c.text for c in format_arithmetic(contribution)]
    assert clauses == [
        "Base 10 points for commitment_met",
        "reduced 60% for finding magnitude",
        "4 points total",
    ]

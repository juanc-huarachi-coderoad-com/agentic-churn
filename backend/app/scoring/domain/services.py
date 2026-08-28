"""Domain services for M6 (scoring) — `architecture/09-clean-architecture-and-
patterns.md`'s named pattern catalog for this module: `AgeingCalculator`,
`BandClassifier`, `IssueGrouper`, `DampingCalculator`, `ScoringCalculator`, plus
`compute_stakes()` (one function, not a 6th named class — P10/YAGNI, it's one
multiplication). Pure functions/classes operating on plain values — no I/O, no
framework imports, no adapters (constitution P8, `.importlinter`'s
`scoring-domain-purity` contract).
"""

import math
from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from app.scoring.domain.entities import FindingLifecycle

# ---------------------------------------------------------------------------
# AgeingCalculator (REQ-M6-09..12, REQ-M6-CAL-01/02)
# ---------------------------------------------------------------------------

_AGEING_RATE = 0.08
_AGEING_CAP = 2.0


class AgeingCalculator:
    """Computes `recency` purely from a finding's lifecycle state — never from the
    finding's own `magnitude`/`confidence`, and never from the previous score."""

    def compute_recency(
        self, lifecycle: FindingLifecycle, *, half_life_days: float | None, as_of: datetime
    ) -> float:
        if lifecycle.state == "open":
            return 1.0

        if lifecycle.state == "resolved":
            if lifecycle.resolved_at is None or half_life_days is None or half_life_days <= 0:
                return 1.0
            days_since_resolved = (as_of - lifecycle.resolved_at).total_seconds() / 86400
            days_since_resolved = max(days_since_resolved, 0.0)
            return float(0.5 ** (days_since_resolved / half_life_days))

        if lifecycle.state == "open_overdue":
            elapsed = lifecycle.business_hours_elapsed
            threshold = lifecycle.threshold_business_hours
            if elapsed is None or threshold is None or threshold <= 0:
                return 1.0
            overdue_ratio = (elapsed - threshold) / threshold
            return min(1.0 + _AGEING_RATE * overdue_ratio, _AGEING_CAP)

        raise ValueError(f"Unknown finding lifecycle state: {lifecycle.state!r}")


# ---------------------------------------------------------------------------
# BandClassifier (REQ-M6-17..19, REQ-M6-CAL-07)
# ---------------------------------------------------------------------------

_AT_RISK_ENTER = 65.0
_AT_RISK_EXIT = 55.0
_WATCH_ENTER = 35.0


def _raw_band(score: float) -> str:
    if score >= _AT_RISK_ENTER:
        return "at_risk"
    if score >= _WATCH_ENTER:
        return "watch"
    return "healthy"


@dataclass(frozen=True)
class BandClassification:
    raw_band: str
    qualifying_band: str
    """The band `consecutive_runs_in_band` is actually counting a streak for —
    persist this (not `raw_band`, not `displayed_band`) into `band_history.band` so
    the next run's `prior_qualifying_band`/`prior_qualifying_streak` inputs are
    consistent with what produced them."""
    displayed_band: str
    consecutive_runs_in_band: int


class BandClassifier:
    """Classifies a score into a band with hysteresis (65 enter / 55 exit for
    `at_risk`) and 2-consecutive-run stickiness for *any* band change.

    Needs two independent pieces of prior state, not one — `band_history`'s own
    (band, consecutive_runs_in_band) tracks the *qualifying candidate*'s own streak,
    while the *displayed* band (the most recent `score_runs.band`) can lag a step
    behind it during a transition. Collapsing these into a single counter can't
    correctly implement "a new candidate needs two consecutive runs before the
    display changes" — REQ-M6-19 — since the moment a candidate first appears, its
    own streak and the currently-displayed band are, by definition, different
    values. Reading the prior *band* here is not the same as reading the prior
    *score* into the arithmetic (REQ-M6-P2 forbids the latter, not this — `spec.md`
    Acceptance Scenario 3: band history is "never fed back into the score
    calculation itself," not "never read at all")."""

    def classify(
        self,
        score: float,
        *,
        prior_displayed_band: str | None,
        prior_qualifying_band: str | None,
        prior_qualifying_streak: int,
    ) -> BandClassification:
        raw = _raw_band(score)

        if prior_displayed_band is None:
            # First-ever run for this account: no prior band to protect via
            # hysteresis — the raw classification displays immediately
            # (spec.md's Edge Cases).
            return BandClassification(
                raw_band=raw,
                qualifying_band=raw,
                displayed_band=raw,
                consecutive_runs_in_band=1,
            )

        # Hysteresis: while displaying at_risk, only a raw band strictly below the
        # 55 exit floor counts as "qualifying for a change" at all.
        if prior_displayed_band == "at_risk" and score >= _AT_RISK_EXIT:
            qualifying_band = "at_risk"
        else:
            qualifying_band = raw

        streak = (
            prior_qualifying_streak + 1
            if qualifying_band == prior_qualifying_band
            else 1
        )

        if qualifying_band == prior_displayed_band:
            displayed_band = prior_displayed_band
        elif streak >= 2:
            # The new candidate has now held for two consecutive runs — REQ-M6-19.
            displayed_band = qualifying_band
        else:
            displayed_band = prior_displayed_band

        return BandClassification(
            raw_band=raw,
            qualifying_band=qualifying_band,
            displayed_band=displayed_band,
            consecutive_runs_in_band=streak,
        )


# ---------------------------------------------------------------------------
# IssueGrouper (REQ-M6-06..08) — one general algorithm, no fixture-specific
# exception (research.md's Decision, corrected during /speckit-analyze)
# ---------------------------------------------------------------------------

_RANK_DECAY = 0.6


@dataclass(frozen=True)
class RawFindingWeight:
    finding_id: UUID
    raw_points: float


@dataclass(frozen=True)
class RankedFinding:
    finding_id: UUID
    rank: int
    rank_factor: float


class IssueGrouper:
    """Ranks findings within a shared issue by raw points (`base × influence ×
    criticality × confidence × magnitude`, recency excluded) descending, and
    assigns the diminishing rank factor (1st 100%, 2nd 60%, 3rd 36%, continuing
    ×0.6 per step). One general algorithm — no per-issue special case."""

    def rank_within_issue(self, weights: list[RawFindingWeight]) -> list[RankedFinding]:
        ordered = sorted(weights, key=lambda w: w.raw_points, reverse=True)
        return [
            RankedFinding(
                finding_id=w.finding_id, rank=i + 1, rank_factor=_RANK_DECAY**i
            )
            for i, w in enumerate(ordered)
        ]


# ---------------------------------------------------------------------------
# DampingCalculator (REQ-M6-05, REQ-M6-CAL-03a)
# ---------------------------------------------------------------------------


class DampingCalculator:
    def compute_weight(self, *, false_alarm_count: int, correct_count: int) -> float:
        weight = (0.5**false_alarm_count) * (1.15**correct_count)
        return max(0.0, min(weight, 1.0))


# ---------------------------------------------------------------------------
# ScoringCalculator (REQ-M6-01, REQ-M6-13..16)
# ---------------------------------------------------------------------------

_POSITIVE_CAP_RATIO = 0.25
_SCORE_SATURATION = 33.0


@dataclass(frozen=True)
class FindingWeightInputs:
    base: float
    influence: float
    criticality: float
    confidence: float
    magnitude: float
    recency: float
    damping: float
    rank_within_issue_factor: float


class ScoringCalculator:
    """Deliberately unintelligent — plain arithmetic a person can verify on paper
    (P2). No model call anywhere in this class or anything it calls."""

    def compute_points(self, inputs: FindingWeightInputs) -> float:
        return (
            inputs.base
            * inputs.influence
            * inputs.criticality
            * inputs.confidence
            * inputs.magnitude
            * inputs.recency
            * inputs.damping
            * inputs.rank_within_issue_factor
        )

    def apply_positive_cap(
        self, *, total_negative_points: float, total_positive_points: float
    ) -> float:
        cap = _POSITIVE_CAP_RATIO * total_negative_points
        return min(total_positive_points, cap)

    def points_to_score(self, total_points: float) -> float:
        # e^(-total_points/33) underflows to exactly 0.0 in float64 for very large
        # total_points, which would otherwise yield score == 100.0 exactly —
        # violating REQ-M6-16 ("never reaches 100") and score_runs.score's DB CHECK
        # (score < 100). `min(raw, 99.99)` is deliberate over an `if raw >= X: return
        # 99.99` threshold: score_runs.score is NUMERIC(5,2), so Postgres rounds any
        # stored value >= 99.995 up to 100.00 before evaluating the CHECK — a raw
        # value like 99.9999999999774 (float64 rarely lands on exactly 100.0) passed
        # a naive `raw >= 100.0` guard uncaught, then failed the CHECK anyway once
        # rounded at insert (specs/030-real-warehouse-connector — first surfaced once
        # ComputeRollupsUseCase started actually feeding the Usage reader real data).
        # A hard `if raw >= 99.995: return 99.99` threshold fixes that but introduces
        # a discontinuity — total_points values straddling the threshold would
        # produce a LOWER score just past it (99.994... -> 99.99), breaking
        # tests/scoring/test_monotonicity.py's invariant. `min(raw, 99.99)` has no
        # such jump: it's non-decreasing everywhere, a flat 99.99 plateau for every
        # raw >= 99.99 (comfortably clear of the 99.995 rounding boundary) and the
        # real asymptotic value below that.
        raw = 100.0 * (1.0 - math.exp(-total_points / _SCORE_SATURATION))
        return min(raw, 99.99)


def compute_stakes(
    *, contract_value_band: str, renewal_date: date, as_of: date
) -> float:
    """`stakes = contract_value_multiplier × renewal_proximity_factor` (REQ-M6-27/28).
    New seed-default constants pinned by this feature (`spec.md` FR-012, the
    2026-08-14 clarification — no prior calibration existed for this formula, unlike
    every other scoring number)."""
    contract_value_multiplier = {"strategic": 1.5, "standard": 1.0, "smb": 0.6}[
        contract_value_band
    ]
    days_until_renewal = (renewal_date - as_of).days
    renewal_proximity_factor = max(0.5, min(2.0 - (days_until_renewal / 90.0), 2.0))
    return contract_value_multiplier * renewal_proximity_factor

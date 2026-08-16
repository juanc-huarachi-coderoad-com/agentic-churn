"""Pure decision logic per reader (M5) — no I/O, unit-testable with plain values.
Mirrors `app.scoring.domain.services`'s own shape: adapters fetch raw rows, these
functions decide what a finding is worth (`research.md`'s Decisions).
"""

import math
from dataclasses import dataclass
from uuid import UUID

import hdbscan

from app.readers.domain.entities import (
    CandidateTicket,
    FailedCheck,
    ResponsePairInfo,
    ValidationGateResult,
)
from app.scoring.domain.entities import Finding

# ---------------------------------------------------------------------------
# Commitment (REQ-M5-07)
# ---------------------------------------------------------------------------

_COMMITMENT_MET_THRESHOLD_FRACTION = 0.5


@dataclass(frozen=True)
class CommitmentFinding:
    finding_type: str
    magnitude: float
    confidence: float


def evaluate_commitment(pair: ResponsePairInfo) -> CommitmentFinding | None:
    """`confidence = 1.0` always — exact arithmetic, zero uncertainty (the same
    reasoning `data-base/05-schema-reasoning.md`'s own notes give for `fnd-1`).
    Emits nothing when there's no real threshold to compare against (no matching
    commitment configured, `spec.md`'s Edge Cases)."""
    if pair.threshold_business_hours is None or pair.threshold_business_hours <= 0:
        return None
    if pair.business_hours_elapsed is None:
        return None

    elapsed = pair.business_hours_elapsed
    threshold = pair.threshold_business_hours

    if pair.state == "open_overdue" or (pair.state == "resolved" and elapsed > threshold):
        overdue_ratio = (elapsed - threshold) / threshold
        return CommitmentFinding(
            finding_type="broken_response_promise",
            magnitude=min(max(overdue_ratio, 0.0), 1.0),
            confidence=1.0,
        )

    if pair.state == "resolved" and elapsed <= _COMMITMENT_MET_THRESHOLD_FRACTION * threshold:
        return CommitmentFinding(
            finding_type="commitment_met",
            magnitude=min(max(1.0 - (elapsed / threshold), 0.0), 1.0),
            confidence=1.0,
        )

    return None


# ---------------------------------------------------------------------------
# Usage (REQ-M5-08, REQ-M2-06)
# ---------------------------------------------------------------------------

_Z_SCORE_THRESHOLD = 2.0
_USAGE_MIN_SAMPLES = 3


def z_score(historical_values: list[float], new_value: float) -> float | None:
    """`None` if there aren't enough historical samples to compute a meaningful
    distribution from (FR-008) — the minimum-sample abstention floor."""
    if len(historical_values) < _USAGE_MIN_SAMPLES:
        return None
    mean = sum(historical_values) / len(historical_values)
    variance = sum((v - mean) ** 2 for v in historical_values) / (len(historical_values) - 1)
    stdev = math.sqrt(variance)
    if stdev == 0:
        return None
    return (new_value - mean) / stdev


def is_usage_deviation(z: float) -> bool:
    return abs(z) > _Z_SCORE_THRESHOLD


def usage_deviation_magnitude(z: float) -> float:
    """Bounded to `[0, 1]` — how far outside normal the value fell, saturating
    rather than growing unbounded for an extreme outlier."""
    return min(abs(z) / (_Z_SCORE_THRESHOLD * 2), 1.0)


# ---------------------------------------------------------------------------
# Absence (REQ-M5-10)
# ---------------------------------------------------------------------------

_ABSENCE_CONFIDENCE = 0.85
_ABSENCE_MAGNITUDE_CADENCE_MULTIPLE = 2.0


def absence_magnitude(
    *, silence_days: float | None, cadence_days: float
) -> float:
    """`silence_days=None` means no prior contact ever recorded — maximally
    severe. Otherwise scaled against how many cadence periods have elapsed
    without contact (`research.md`'s Decision, corrected during implementation
    to use the real event payload's fields, not an assumed `missed_count`)."""
    if silence_days is None:
        return 1.0
    if cadence_days <= 0:
        return 1.0
    return min(silence_days / (_ABSENCE_MAGNITUDE_CADENCE_MULTIPLE * cadence_days), 1.0)


def absence_confidence() -> float:
    return _ABSENCE_CONFIDENCE


# ---------------------------------------------------------------------------
# Relationship (REQ-M5-11)
# ---------------------------------------------------------------------------

_RELATIONSHIP_MAGNITUDE = 0.5
_RELATIONSHIP_CONFIDENCE = 0.7


def relationship_change_finding() -> tuple[float, float]:
    """Fixed `(magnitude, confidence)` — this reader's reduced-strength signal
    genuinely can't distinguish "quietly stepping back" from "just had a quiet
    month" as precisely as a full-strength Phase 2 reader could, so a moderate,
    honest fixed pair is more accurate than a false-precision formula
    (`research.md`'s Decision)."""
    return _RELATIONSHIP_MAGNITUDE, _RELATIONSHIP_CONFIDENCE


# ---------------------------------------------------------------------------
# Recurrence (REQ-M5-09)
# ---------------------------------------------------------------------------

_RECURRENCE_MIN_CLUSTER_SIZE = 2
_RECURRENCE_MAGNITUDE_DIVISOR = 3.0


@dataclass(frozen=True)
class ClusteredGroup:
    members: list[CandidateTicket]
    confidences: list[float]


def cluster_candidates(
    candidates: list[CandidateTicket], vectors: list[list[float]]
) -> list[ClusteredGroup]:
    """HDBSCAN over the full candidate corpus every run (`min_cluster_size = 2` —
    a single ticket can never recur against itself; 2026-08-14 clarification: no
    incremental clustering). Pure over already-computed vectors — no I/O.

    `min_samples=1, allow_single_cluster=True` (found necessary during
    implementation): HDBSCAN's defaults estimate local density from each
    point's nearest neighbors, which is unreliable at this feature's small
    candidate-corpus sizes (a handful of tickets) — verified empirically to
    misclassify even exact-duplicate points as noise otherwise. These two
    settings together make a single close neighbor sufficient evidence of
    density and let a single genuine cluster surface even when nothing else in
    the corpus forms a second one — but also make HDBSCAN over-eager at these
    small sizes, verified to sometimes lump several *unrelated* singletons into
    one shared cluster (not noise) purely because there's too little data for
    its density estimate to separate them. A cluster is only trusted here if
    its members are genuinely close (`_RECURRENCE_MAX_PAIRWISE_DISTANCE`) — a
    conservative floor, favoring a missed recurrence over a fabricated one
    (`spec.md`'s "abstain rather than manufacture a low-value opinion"
    principle, applied to this reader too)."""
    if len(candidates) < _RECURRENCE_MIN_CLUSTER_SIZE:
        return []

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=_RECURRENCE_MIN_CLUSTER_SIZE,
        min_samples=1,
        allow_single_cluster=True,
    )
    labels = clusterer.fit_predict(vectors)
    probabilities = clusterer.probabilities_

    groups: dict[int, list[int]] = {}
    for index, label in enumerate(labels):
        if label == -1:
            continue
        groups.setdefault(int(label), []).append(index)

    return [
        ClusteredGroup(
            members=[candidates[i] for i in indices],
            confidences=[float(probabilities[i]) for i in indices],
        )
        for indices in groups.values()
        if _max_pairwise_distance([vectors[i] for i in indices])
        <= _RECURRENCE_MAX_PAIRWISE_DISTANCE
    ]


_RECURRENCE_MAX_PAIRWISE_DISTANCE = 1.0


def _max_pairwise_distance(vectors: list[list[float]]) -> float:
    if len(vectors) < 2:
        return 0.0
    return max(
        math.dist(vectors[i], vectors[j])
        for i in range(len(vectors))
        for j in range(i + 1, len(vectors))
    )


def recurrence_magnitude(cluster_size: int) -> float:
    return min((cluster_size - 1) / _RECURRENCE_MAGNITUDE_DIVISOR, 1.0)


# ---------------------------------------------------------------------------
# M5a validation gate — four pure checks (REQ-M5A-01), no I/O
# (specs/007-model-findings, research.md Decision 6)
# ---------------------------------------------------------------------------


def finding_schema_valid(finding: Finding, thresholds: tuple[float, int] | None) -> bool:
    """`thresholds is None` means `finding_type` isn't a configured row — a
    schema failure in its own right (`research.md` Decision 6.1), not a
    separate code path."""
    if thresholds is None:
        return False
    if not (0.0 <= finding.magnitude <= 1.0):
        return False
    if not (0.0 <= finding.confidence <= 1.0):
        return False
    return bool(finding.cited_event_ids)


def cited_events_exist(cited_ids: tuple[UUID, ...], existing_ids: set[UUID]) -> bool:
    return all(cid in existing_ids for cid in cited_ids)


def sufficient_evidence(cited_ids: tuple[UUID, ...], min_evidence_count: int) -> bool:
    return len(cited_ids) >= min_evidence_count


def confidence_at_floor(confidence: float, confidence_floor: float) -> bool:
    """Inclusive — confidence exactly equal to the floor passes (`spec.md`'s
    Edge Cases)."""
    return confidence >= confidence_floor


def evaluate_finding(
    finding: Finding,
    thresholds: tuple[float, int] | None,
    existing_ids: set[UUID],
) -> ValidationGateResult:
    """The gate's combining function — Chain of Responsibility over the four
    fixed checks (`architecture/09-clean-architecture-and-patterns.md`), each
    independent and order-agnostic. A finding failing more than one check
    produces one `FailedCheck` per failed check (spec.md's User Story 3,
    Acceptance Scenario 3)."""
    failed: list[FailedCheck] = []

    if not finding_schema_valid(finding, thresholds):
        failed.append(
            FailedCheck(
                check_name="schema_invalid",
                expected="magnitude/confidence in [0, 1], non-empty cited_event_ids, "
                "a configured finding_type",
                actual=(
                    f"magnitude={finding.magnitude}, confidence={finding.confidence}, "
                    f"cited_event_ids={len(finding.cited_event_ids)}, "
                    f"finding_type={finding.finding_type!r} "
                    f"({'configured' if thresholds is not None else 'not configured'})"
                ),
            )
        )
        if thresholds is None:
            # Nothing to check evidence count/confidence against — this is
            # the only failure this finding can meaningfully report.
            return ValidationGateResult(passed=False, failed_checks=tuple(failed))

    if not cited_events_exist(finding.cited_event_ids, existing_ids):
        missing = sorted(str(cid) for cid in finding.cited_event_ids if cid not in existing_ids)
        failed.append(
            FailedCheck(
                check_name="cited_event_missing",
                expected="every cited_event_id exists as a real row in events",
                actual=f"missing: {missing}",
            )
        )

    # Reachable only when thresholds is not None: the `thresholds is None`
    # branch above always returns before this point.
    assert thresholds is not None
    confidence_floor, min_evidence_count = thresholds
    if not sufficient_evidence(finding.cited_event_ids, min_evidence_count):
        failed.append(
            FailedCheck(
                check_name="insufficient_evidence",
                expected=f">= {min_evidence_count}",
                actual=str(len(finding.cited_event_ids)),
            )
        )
    if not confidence_at_floor(finding.confidence, confidence_floor):
        failed.append(
            FailedCheck(
                check_name="confidence_below_floor",
                expected=f">= {confidence_floor}",
                actual=str(finding.confidence),
            )
        )

    return ValidationGateResult(passed=len(failed) == 0, failed_checks=tuple(failed))

"""Narrator (M7) domain value objects — this module's first real content
(feature 001 left `app.narrator` an empty scaffold). `app.narrator.domain.
services`'s pure fact-check function consumes/produces these, no I/O.
"""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class RankedContribution:
    """One `score_contributions` row for the run being narrated, in the
    scoring engine's own order — the Narrator never re-sorts this list
    (REQ-M7-01, REQ-M7-P2)."""

    finding_id: UUID
    finding_type: str
    points: float
    is_positive: bool
    cited_event_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class IssueSummary:
    """The fallback template's `top_issue` — `label`/`points` only, no
    finding-level detail (`architecture/06-error-handling.md`'s
    deterministic headline)."""

    label: str
    points: float


@dataclass(frozen=True)
class VerifiedFactSet:
    """Every number and name that legitimately exists in one run's
    structured input — built once, before any generation call."""

    numbers: frozenset[str] = field(default_factory=frozenset)
    names: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class FactCheckResult:
    passed: bool
    extracted_numbers: frozenset[str] = field(default_factory=frozenset)
    extracted_names: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class NarratedReason:
    text: str
    points: float
    evidence_event_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class NarratedAction:
    text: str
    owner: str
    due_date: str
    playbook_id: UUID


@dataclass(frozen=True)
class NarratorOutput:
    """The use case's final result, mapped 1:1 onto `narrator_outputs`'
    columns."""

    headline: str
    reasons: tuple[NarratedReason, ...]
    actions: tuple[NarratedAction, ...]
    fact_check_passed: bool
    prompt_version: str

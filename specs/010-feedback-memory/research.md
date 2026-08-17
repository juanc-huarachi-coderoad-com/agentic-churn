# Phase 0 Research: Feedback Memory

All research below comes from reading the actual, already-shipped codebase
(features 001–009), not from prose docs alone — several findings correct
prose that was never actually implemented the way it was written.

## Decision 1 — `pattern_signature` is `reader_type+finding_type`, two components, not three

**Finding**: `data-base/07-schema-feedback.md` documents `pattern_signature`
as `reader_type + finding_type + event_signature_class` (three components).
The already-shipped, already-verified scoring engine (feature 004,
`RecomputeScoreUseCase.execute`, `backend/app/scoring/application/
use_cases.py:155`) constructs and reads it as literally
`f"{finding.reader_type}+{finding.finding_type}"` — **two** components. The
`Finding` domain entity it operates on
(`backend/app/scoring/domain/entities.py`) doesn't even carry an event
type, only `cited_event_ids` (opaque UUIDs). The worked examples in
`data-base/07-schema-feedback.md` itself (`relationship+relationship_change`)
and `examples/01-end-to-end-walkthrough.md` §14 both already match the
2-component format — only the field-level prose description row was stale.

**Decision**: This feature (the write side) constructs `pattern_signature`
in the exact same 2-component format the already-running reader expects.
Building a 3-component writer against a 2-component reader would make
every `damping_weights` lookup miss silently — `DampingRepositoryPort.
get_weight()` already defaults to `1.0` when no row matches (by design, for
an unseeded pattern), so a format mismatch would be indistinguishable from
"no feedback yet ever recorded" — a severe, silent correctness bug, not a
loud failure.

**Corrective actions taken**:
- `specs/010-feedback-memory/spec.md` corrected in place (Clarifications
  section, FR-005, Key Entities, Edge Cases, Assumptions) — see its
  Clarifications session's "Corrected during `/speckit-plan`" note.
- `data-base/07-schema-feedback.md`'s `pattern_signature` field description
  corrected to match, per this repo's own "fix a cross-file inconsistency
  everywhere it appears" convention (`AGENTS.md`).

**Alternatives considered**: Add the event-type component to the scoring
engine's read side instead (matching the original 3-component prose).
Rejected — the fully-shipped feature 004 module is protected by P9's
golden-replay/reconciliation/monotonicity gates; touching its `damping`
consumption for a documentation preference the module's own tests never
required would add risk for zero product value, and no requirement
(`REQ-M4-*`, `REQ-M6-CAL-03*`) actually needs the finer granularity — a
finding type already implies enough specificity (`finding_type_config` is
itself keyed by `finding_type` alone, with no event-type breakdown).

## Decision 2 — `pattern_signature()` becomes one shared, canonical function, not two independent inline copies

**Finding**: Today, the 2-component format exists only as an inline
f-string in `RecomputeScoreUseCase.execute`. This feature needs the
identical format on the write side. Two independently-typed f-strings in
two different modules is exactly the kind of duplication a future edit
could silently desynchronize.

**Decision**: Extract a single pure function,
`pattern_signature(reader_type: str, finding_type: str) -> str`, into
`backend/app/context/domain/damping_calculator.py` — the file
`decisions/02-repo-and-tooling.md`'s module→package mapping table already
names for M4 ("Implements the damping formula... pure function, no I/O").
`app.scoring.application.use_cases.RecomputeScoreUseCase` is updated to
import and call it instead of inlining the f-string — a behavior-preserving
refactor (identical output for identical inputs), verified by re-running
feature 004's existing golden-replay/reconciliation/monotonicity suite
unchanged. `app.context.domain` → is imported by `app.scoring.application`
here; `app.experience` (Decision 3) imports the same helper. This is
architecturally legal under `.importlinter`'s `global-dependency-rule`
(cross-module domain→domain imports are unrestricted; only a module's own
adapters→domain direction is forbidden) and matches feature 009's own
precedent of `app.experience.domain.services.verify_facts` reusing
`app.narrator.domain.services.fact_check` cross-module rather than
redefining it — P8's "an entity/rule that spans modules is defined once, in
the module that owns its lifecycle, and imported by the others."

**Alternatives considered**: Leave the scoring engine's inline f-string
untouched and duplicate an identical helper inside `app.context`. Rejected
— guarantees eventual drift with no compensating benefit; the refactor is a
one-line change with an existing test suite to catch any regression
immediately.

## Decision 3 — One verdict UI, reused via existing click-through navigation, not three duplicated inline controls

**Finding**: `frontend/src/evidence/evidence-panel.tsx` already carries a
forward-looking comment: *"No feedback controls here — out of this
feature's scope (FR-014, feature 010's job)"* — feature 006 explicitly
reserved this exact panel for this exact feature. The dashboard's
`ContributionBars` component already opens this same panel via
`onSelect(scoreContributionId)`, and the Ask agent's `delta_breakdown`/
`ranked_issues` answers already carry `score_contribution_id` in their
`causes`/`ranked_issues` prop arrays server-side
(`backend/app/experience/adapters/ask_agent_graph.py:224`,
`c["score_contribution_id"]`) — it's simply not yet exposed in the
frontend's local `Cause` TypeScript type (`answer-renderer.tsx`).

**Decision**: The verdict controls (`correct`/`false_alarm`/`resolved`
buttons) and the `disclosure_text` display live in exactly one place —
`EvidencePanel` — which every "finding-bearing card" REQ-M4-01 names
already opens or can open: the dashboard's contribution bar already does;
the Ask agent's `delta_breakdown`/`ranked_issues` cause rows gain the same
`onSelect`-style click-through by adding `score_contribution_id` to the
frontend `Cause` type (zero backend change needed — the field is already
in the API response, just untyped/unread on the frontend today) and
threading an `onOpenEvidence` callback down through `AnswerRenderer`,
mirroring the already-established `onOpenDraftComposer` callback-threading
pattern from feature 009 exactly. This satisfies REQ-M4-01's "any
finding-bearing card" without duplicating verdict UI three times.

**Alternatives considered**: Inline verdict buttons directly on the
dashboard's `ContributionBars` row and on each Ask answer's cause row.
Rejected as needless duplication (P10/YAGNI) — three copies of the same
three buttons and disclosure text, three times the surface area for a
copy/paste bug, when one shared detail panel already exists and was
explicitly reserved for this purpose.

## Decision 4 — `disclosure_text` is a new, additive field, separate from the evidence panel's existing "prior feedback" arithmetic clause

**Finding**: `backend/app/experience/domain/services.py`'s
`format_arithmetic()` (feature 006) already renders a `"prior feedback"`
clause in `EvidenceTraceResponse.arithmetic_explanation`/`what_changed`
whenever a *specific, already-scored* `score_contributions.damping` value
is non-neutral — a frozen, historical, percentage-phrased line ("prior
feedback reduced this by 50%"), computed once at scoring time and never
updated afterward. This is a different mechanism from REQ-M4-04's
requirement: a *live*, exact, precomputed sentence
(`damping_weights.disclosure_text`, e.g. "weight reduced — your team
dismissed this pattern twice") that must reflect the pattern's *current*
state regardless of which specific score run any one card is showing.

**Decision**: Add a new, additive `disclosure_text: str | None` field to
`EvidenceTraceResponse`, sourced live from `damping_weights` via the
finding's `pattern_signature` — present only when the pattern's current
`weight < 1.0` (`null` otherwise, never an empty string, matching this
codebase's "absent, not empty" convention for optional narrator/coverage
fields). This is additive alongside the existing arithmetic clause, not a
replacement for it — the two answer different questions ("what happened to
this specific score" vs. "what does the team currently think of this
pattern").

## Decision 5 — Read-then-upsert `damping_weights`, not a single atomic SQL statement, at this scale

**Finding**: Concurrent verdict submissions on the exact same
`pattern_signature` within the same instant are structurally rare — this
system is single-deployment-per-client (`architecture/
03-technology-stack.md`), used by one small CS team clicking one button at
a time on one dashboard.

**Decision**: `RecordFeedbackVerdictUseCase` reads the current
`damping_weights` row (or a zeroed default if none exists yet, FR-008),
computes the next counts and weight in the pure domain layer, then upserts
the full row (`INSERT ... ON CONFLICT (pattern_signature) DO UPDATE`).
This is a small, accepted, documented race window (two verdicts on the
same pattern within milliseconds could read-before-write and lose one
increment) rather than a `SELECT ... FOR UPDATE`/serializable-transaction
guarantee — consistent with this codebase's general MVP-scale pragmatism
(no message broker, no distributed lock anywhere else in the system either,
`architecture/03-technology-stack.md`).

**Alternatives considered**: A single SQL statement doing the increment and
recompute server-side (e.g. a `weight = LEAST(1.0, GREATEST(0.0, ...))`
expression inline in the `UPDATE`). Rejected — it would duplicate the
damping formula in SQL *and* in the pure Python domain function
(`compute_weight`), the exact double-implementation risk P9's "one
canonical, unit-tested pure function" discipline exists to avoid; the
formula must be verified once, in Python, with plain `assert` statements
per P9, not re-derived and re-trusted in SQL.

## Decision 6 — `false_alarm`/`correct` require `finding_id`; issue-scoped verdicts are `resolved`-only in practice

Already resolved and recorded in `spec.md`'s Clarifications session
(2026-08-16) — restated here only to note its implementation shape: FR-005a
is enforced at the application layer (`RecordFeedbackVerdictUseCase`
raises a typed error the router maps to `422`), not only by the DB's
`CHECK (finding_id IS NOT NULL OR issue_id IS NOT NULL)` constraint, which
is deliberately weaker (it doesn't distinguish by verdict type).

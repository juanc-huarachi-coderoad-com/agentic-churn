# Implementation Plan: Feedback Memory

**Branch**: `010-feedback-memory` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/010-feedback-memory/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build "the learning loop" — `RecordFeedbackVerdictUseCase` in
`backend/app/context/application/use_cases.py`, alongside the existing
`SubmitProfileUseCase` (`decisions/02-repo-and-tooling.md`'s ratified
module→package mapping: M4 lives inside `app.context`, sharing the module
with M3). The use case resolves the verdict's target finding (directly via
`finding_id`, or — for an issue-scoped `resolved` verdict only, per
Clarifications 2026-08-16 — the issue's top-ranked finding), reads its
`reader_type`/`finding_type`, builds a `pattern_signature` in the **exact**
2-component format the already-shipped scoring engine already reads
(`research.md` Decision 1 — a real, plan-time-discovered correction: the
prose docs described a 3-component key that was never actually
implemented), recomputes that pattern's damping weight via one pure,
unit-tested function (`compute_weight`, REQ-M6-CAL-03a), and upserts
`feedback_verdicts`/`damping_weights`. `backend/app/scoring/application/
use_cases.py`'s inline pattern-signature f-string is refactored to import
the same canonical function (`research.md` Decision 2), a
behavior-preserving change re-verified against feature 004's existing
golden-replay/reconciliation/monotonicity suite. On the read side,
`GetEvidenceTraceUseCase` (`app.experience`, feature 006) gains one
additive field, `disclosure_text`, sourced live from `damping_weights` —
distinct from feature 006's own existing frozen "prior feedback" arithmetic
clause (`research.md` Decision 4). On the frontend, `EvidencePanel`
(`frontend/src/evidence/evidence-panel.tsx`) — which has carried an
explicit "no feedback controls here — feature 010's job" comment since
feature 006 — gets its first real verdict buttons and disclosure text; the
Ask agent's `delta_breakdown`/`ranked_issues` answers gain a click-through
into that same panel by exposing a `score_contribution_id` field their
backend response already includes but the frontend never typed
(`research.md` Decision 3 — one shared verdict UI, not three duplicated
ones). Zero new routes beyond the one already-documented
`POST /api/feedback` (`architecture/07-api-spec.md`), zero new environment
variables, zero new dependencies.

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript + React 18
(frontend) — unchanged from features 001–009; touches both sides of the
stack, like 006/008/009.

**Primary Dependencies (new in this feature)**: None. No new Python
package, no new frontend package.

**Storage**: PostgreSQL 16 — **no migration**. `feedback_verdicts` and
`damping_weights` already exist since feature 001's straight-DDL-import
migration (`data-model.md`, confirmed by reading the actual DDL file, not
the prose schema doc alone — which needed a correction, `research.md`
Decision 1). This feature is the first real writer of both tables.

**Testing**: pytest + `hypothesis` (backend), Vitest (frontend).
`compute_weight`/`build_disclosure_text`/`pattern_signature` are pure and
directly unit-tested against REQ-M6-CAL-03a's own worked values
(`0.500`, `0.250`, `0.2875`) with plain asserts — no DB, no LLM, matching
`fact_check`/the draft composer's five check functions' own precedent.
`RecordFeedbackVerdictUseCase` gets its three ports faked in its own test.
A real-DB/real-route test exercises `POST /api/feedback` end to end against
the worked-example fixture, confirming `damping_weights` state after 1 and
2 `false_alarm` verdicts and one recovering `correct` verdict, plus the
FR-005a rejection case (`issue_id`-only `false_alarm`, expect `422`).
Feature 004's existing golden-replay/reconciliation/monotonicity suite is
re-run unchanged to confirm `research.md` Decision 2's refactor is
behavior-preserving (same `pattern_signature` string, same
`RecomputeScoreUseCase` output, for identical input). A static scan
(`test_no_llm_imports.py`) confirms REQ-M4-05/SC-005 across **every** file
this feature touches — not just the new `app.context` code, but also the
additive `app.experience` disclosure-read code and the refactored
`app.scoring` line — since a verdict-reachable code path could in
principle run through any of the three (`/speckit-analyze` finding C1,
2026-08-16).

**Target Platform**: Same Docker Compose stack as features 001–009 — no
new service, no `docker-compose.yml` change, no new `Settings` field, no
new env var.

**Project Type**: Web application — backend (Python/FastAPI) and frontend
(React/TypeScript) both change. Backend: extended `app.context.{domain,
application,adapters}` (new domain/application code in an
already-established module — M4's designated home per `decisions/
02-repo-and-tooling.md`), one new route; a small, behavior-preserving
refactor inside `app.scoring.application.use_cases`; an additive field on
`app.experience`'s `GetEvidenceTraceUseCase`/`EvidenceTraceResponse`.
Frontend: `frontend/src/evidence/` (already has an empty, explicitly
reserved slot) gets its first verdict controls; `frontend/src/ask/
components/answer-renderer.tsx`'s `Cause` type gains one field already
present in the API response.

**Performance Goals**: None beyond FR-002's qualitative "single click, no
modal, no confirmation toast" (spec §11.6) — `POST /api/feedback` is a
synchronous write of two small rows, no LLM call, no external dependency;
no resilience budget applies (`architecture/06-error-handling.md`'s budget
table only covers the six LLM touchpoints — this isn't one of them).

**Constraints**: REQ-M4-P1/P2 — structural, not conventions. No control or
code path anywhere damps an entire reader type in one action (P2); a
damped finding is never hidden, only labeled (P1) — enforced by construction
(`GetEvidenceTraceUseCase`/dashboard/evidence-panel queries never filter on
`damping_weights.weight`, only ever *display* it). `false_alarm`/`correct`
require a specific `finding_id` (FR-005a) — the one new restriction this
feature's own `/speckit-clarify` session added beyond REQ-M4's original
text, closing a real P2-adjacent risk the base requirement didn't
explicitly anticipate (a multi-reader issue's verdict silently touching
several different readers' weights at once).

**Scale/Scope**: Fixture-driven, same as every prior feature — the real,
already-ingested/read/scored/validated Meridian ledger. No Narrator/Ask
agent/Draft composer dependency — this feature only needs a `score_run`
with at least one validated finding, so its own quickstart/tests can run
against a stack as early as feature 007's state, though the full frontend
wiring (Decision 3's Ask-agent click-through) exercises feature 008's
already-shipped `delta_breakdown`/`ranked_issues` components too.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| **P1 Evidence or It Does Not Exist** | Yes — every verdict resolves to a real, already-validated `finding_id` (`cited_event_ids` non-empty by construction, unchanged existing schema); a verdict can never be recorded against a nonexistent or unvalidated finding (`FindingNotFoundError` → `404`) | **Pass** — FR-005, data-model.md |
| **P2 The Model Interprets, Code Calculates** | Yes, directly — `compute_weight` is plain arithmetic (`clamp(0.5^fa × 1.15^c, 0, 1)`), no model call anywhere in this feature; `app.context.domain`/`app.scoring.domain` remain LLM-import-free, unchanged | **Pass** — `.importlinter`'s `scoring-domain-purity` contract untouched; no new contract needed for `app.context.domain` (no forbidden-import rule for it exists yet, but this feature adds none of anthropic/openai to it either) |
| **P3 Each Component Refuses to Do the Next One's Job** | Yes — feedback memory only counts and looks up; it never re-scores (that stays `app.scoring`'s job, reading the weight this feature writes), never re-ranks, never rewrites a reader's output | **Pass** — FR-009, FR-014 |
| **P4 A Human Always Sends** | N/A — no messaging capability in this feature | **N/A** |
| **P5 Admit What We Cannot See** | Yes — `disclosure_text` is never fabricated or defaulted to a generic string when a pattern has no verdict history; it's `null`/absent, not an empty or misleading placeholder (`research.md` Decision 4) | **Pass** — FR-011, Edge Cases |
| **P6 Silence Is a Success State** | Yes — a pattern with no verdicts shows no disclosure at all; feedback memory never manufactures a "learning happened" signal where none did | **Pass** — Acceptance Scenario 2 (Story 2) |
| **P7 Context Over Sentiment** | N/A — no tone/sentiment analysis in this feature | **N/A** |
| **P8 Clean Architecture: the Dependency Rule Is Law** | Yes — all new code lands exactly where `decisions/02-repo-and-tooling.md` already assigns M4 (`app.context.{domain,application,adapters}`); the one cross-module import (`app.scoring.application` → `app.context.domain.pattern_signature`, and `app.experience` → the same) is domain→domain, the same direction feature 009 already established as legal and precedented (`verify_facts` reusing `fact_check`) | **Pass** — `research.md` Decisions 2/4; no `.importlinter` config change needed (cross-module domain imports are already unrestricted by the existing `global-dependency-rule` contract) |
| **P9 Test-First Determinism** | Yes — `compute_weight`/`build_disclosure_text`/`pattern_signature` are pure, unit-tested with plain asserts against REQ-M6-CAL-03a's own worked values; feature 004's golden-replay/reconciliation/monotonicity suite is re-run unchanged to prove Decision 2's refactor is behavior-preserving, not assumed | **Pass — no Complexity Tracking exception** |
| **P10 Simplicity Over Speculative Generality (YAGNI)** | Yes — no new table, no new top-level module (M4 already has a designated home), no new orchestration; the read-then-upsert (not a locking transaction) is the deliberately simpler choice for this scale (`research.md` Decision 5); one shared verdict UI reused via existing click-through navigation, not three duplicated inline controls (`research.md` Decision 3) | **Pass** |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | Yes — `frontend/src/evidence/` stays feature-oriented; the new `POST /api/feedback` client call follows the same TanStack Query mutation pattern already used elsewhere; the `Cause` type gains a typed field instead of an untyped access | **Pass** |
| Full-Stack §4 Testing Strategy | Yes — pure-function unit coverage plus a real-DB/real-route integration test, matching every prior feature's shape | **Pass** — see Testing above |
| Full-Stack §5 Security & Quality Gates | Yes — `submitted_by_user_id` sourced from the bearer token, never the request body, matching every existing "who did this" column's discipline (`AGENTS.md`) | **Pass** |

**No violations requiring justification.** The one notable design choice —
read-then-upsert instead of a fully atomic locking write — is documented
and justified in `research.md` Decision 5, not a Constitution violation
(no principle mandates transactional isolation at this scale; P10 favors
the simpler choice).

**Post-`/speckit-clarify` note (2026-08-16)**: Two questions resolved
during clarification (pattern-signature composition, issue-scoped verdict
matching) — see spec.md's Clarifications section. One of those answers was
then itself corrected during this planning pass once the actual shipped
scoring-engine code was read (`research.md` Decision 1) — spec.md's
Clarifications entry documents the correction in place rather than
re-running `/speckit-clarify`, matching feature 009's own precedent for a
plan-time correction to a clarified answer.

## Project Structure

### Documentation (this feature)

```text
specs/010-feedback-memory/
├── plan.md              # This file
├── research.md          # Phase 0 output — 6 decisions, 2 of which
│                         #   correct stale prose against real shipped code
├── data-model.md         # Phase 1 output — new domain/application/adapter
│                         #   shapes in app.context; additive field in
│                         #   app.experience; zero migration
├── contracts/
│   └── feedback.md       # Phase 1 output — POST /api/feedback (first
│                         #   real implementation of an already-documented
│                         #   route) + EvidenceTraceResponse.disclosure_text
└── quickstart.md         # Phase 1 output — verdict → weight → disclosure,
                          #   the FR-005a rejection case, the immutable-
                          #   history check, the no-LLM-import check
```

### Source Code (repository root)

Extends `backend/app/context/` (feature 003's module, M3+M4 per
`decisions/02-repo-and-tooling.md`) with M4's first real code; makes one
small, behavior-preserving refactor inside `backend/app/scoring/`; extends
`backend/app/experience/` (features 006/007/008/009's module) with one
additive field. No new top-level backend package.

```text
backend/
├── app/
│   ├── context/
│   │   ├── domain/
│   │   │   ├── damping_calculator.py  # NEW: pattern_signature(),
│   │   │   │                           #   compute_weight() (REQ-M6-CAL-03a),
│   │   │   │                           #   build_disclosure_text()
│   │   │   │                           #   (REQ-M4-04) — all pure, no I/O
│   │   │   └── entities.py            # NEW: DampingWeight,
│   │   │                               #   FindingPatternComponents
│   │   ├── application/
│   │   │   ├── ports.py               # extended: FeedbackFindingReadPort,
│   │   │   │                           #   IssueTopFindingReadPort,
│   │   │   │                           #   FeedbackVerdictRepositoryPort
│   │   │   └── use_cases.py           # extended: RecordFeedbackVerdictUseCase,
│   │   │                               #   VerdictRequiresFindingError,
│   │   │                               #   FindingNotFoundError,
│   │   │                               #   IssueNotFoundError — alongside
│   │   │                               #   the existing SubmitProfileUseCase
│   │   └── adapters/
│   │       ├── sqlalchemy_repository.py  # extended: SqlAlchemyFeedback-
│   │       │                               #   FindingReader,
│   │       │                               #   SqlAlchemyIssueTopFindingReader,
│   │       │                               #   SqlAlchemyFeedbackVerdictRepository
│   │       └── feedback_router.py     # NEW: POST /api/feedback —
│   │                                   #   composition root, matching
│   │                                   #   profile_router.py's existing
│   │                                   #   pattern in the same module
│   ├── scoring/
│   │   └── application/
│   │       └── use_cases.py           # MODIFIED (behavior-preserving):
│   │                                   #   RecomputeScoreUseCase.execute's
│   │                                   #   inline f"{reader_type}+
│   │                                   #   {finding_type}" replaced by
│   │                                   #   app.context.domain.
│   │                                   #   damping_calculator.
│   │                                   #   pattern_signature() (research.md
│   │                                   #   Decision 2) — re-verified against
│   │                                   #   the existing golden-replay/
│   │                                   #   reconciliation/monotonicity suite
│   ├── experience/
│   │   ├── application/
│   │   │   ├── ports.py               # extended: DampingDisclosurePort,
│   │   │   │                           #   DisclosureRecord
│   │   │   └── use_cases.py           # extended: GetEvidenceTraceUseCase
│   │   │                               #   attaches disclosure_text
│   │   │                               #   (research.md Decision 4)
│   │   └── adapters/
│   │       └── sqlalchemy_repository.py  # extended: SqlAlchemyDamping-
│   │                                       #   DisclosureReader;
│   │                                       #   SqlAlchemyFindingReader-
│   │                                       #   equivalent used by evidence
│   │                                       #   gains reader_type read
│   └── main.py                        # extended: registers feedback_router
└── tests/
    ├── unit/
    │   ├── test_damping_calculator.py       # NEW — pure, no DB: REQ-M6-CAL-03a's
    │   │                                     #   worked values (0.500, 0.250,
    │   │                                     #   0.2875), clamp bounds
    │   ├── test_record_feedback_verdict_use_case.py  # NEW — ports faked,
    │   │                                                #   incl. FR-005a,
    │   │                                                #   FindingNotFoundError,
    │   │                                                #   IssueNotFoundError
    │   ├── test_feedback_routes_real_db.py             # NEW — real-DB
    │   │                                                 #   integration:
    │   │                                                 #   verdict → weight
    │   │                                                 #   → disclosure,
    │   │                                                 #   422/404 cases
    │   └── test_no_llm_imports.py                       # NEW — static scan,
    │                                                       #   scoped to every
    │                                                       #   file this feature
    │                                                       #   touches, not just
    │                                                       #   app/context/ (see
    │                                                       #   Testing above)
    └── scoring/
        └── test_recompute_score_use_case.py   # UNCHANGED file, re-run to
                                                  #   confirm research.md
                                                  #   Decision 2's refactor
                                                  #   changes no behavior

frontend/
└── src/
    ├── evidence/
    │   ├── evidence-panel.tsx         # extended: removes the "no feedback
    │   │                               #   controls here" comment; adds
    │   │                               #   three verdict buttons + renders
    │   │                               #   disclosure_text when present
    │   ├── evidence-panel.test.tsx    # extended
    │   ├── use-feedback.ts            # NEW: POST /api/feedback mutation,
    │   │                               #   matching use-evidence.ts's
    │   │                               #   existing TanStack Query pattern
    │   └── types.ts                   # extended: EvidenceTraceResponse
    │                                   #   gains disclosure_text
    └── ask/
        └── components/
            └── answer-renderer.tsx    # extended: Cause type gains
                                        #   score_contribution_id (already
                                        #   in the API response, research.md
                                        #   Decision 3); DeltaBreakdown/
                                        #   RankedIssues rows become
                                        #   clickable via a threaded
                                        #   onOpenEvidence callback,
                                        #   mirroring onOpenDraftComposer's
                                        #   existing precedent

architecture/07-api-spec.md             # extended: EvidenceTraceResponse
                                          #   gains disclosure_text
                                          #   (contracts/feedback.md)
data-base/07-schema-feedback.md         # corrected: pattern_signature's
                                          #   field description fixed from
                                          #   a never-implemented 3-component
                                          #   format to the real 2-component
                                          #   one (research.md Decision 1)
```

**Structure Decision**: Same monorepo, extending `context/` — the module
`decisions/02-repo-and-tooling.md` already assigns M4 to, alongside M3 —
with real code for the first time. One small, deliberately scoped,
behavior-preserving edit inside `scoring/` (extracting a helper, not
changing logic), and one additive field inside `experience/` (reusing
feature 006's own explicitly-reserved slot). No new top-level backend
directory, no new Docker service, no new outbound dependency. On the
frontend, `frontend/src/evidence/` — which has carried a comment naming
this exact feature since feature 006 — gets its first real content; no new
top-level frontend directory, and the Ask agent's answer renderer gains a
typed field for data its backend already sends rather than a new backend
capability.

## Complexity Tracking

> No violations requiring justification — see Constitution Check above.
> This feature adds no new table, no new top-level module, and one
> small, test-verified, behavior-preserving refactor inside
> already-shipped code (`research.md` Decision 2) — flagged here for
> visibility, not because it needs justifying against a principle: it's a
> duplication removal, not new complexity.

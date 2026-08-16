# Implementation Plan: Draft Composer

**Branch**: `009-draft-composer` | **Date**: 2026-08-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/009-draft-composer/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Build "the closer" — `GenerateDraftUseCase` in
`backend/app/experience/application/use_cases.py`, alongside
`GetDashboardUseCase`/`GetEvidenceTraceUseCase`/`GetCoverageUseCase`
(`decisions/02-repo-and-tooling.md`'s ratified *behavior* for M10 — "a plain
`LLMPort` call, no orchestration framework" — realized at the codebase's own
already-established file locations, not the doc's slightly stale literal
filenames; `research.md` Decision 2). The use case reads
a requested issue's own aggregated evidence (a new `IssueReadPort`, since no
existing port aggregates evidence by arbitrary issue — `research.md`
Decision 3), the client profile's `communication_norms` (one additive field
on the already-existing `ClientProfileRecord`), real thread history (reused
from feature 008's `LedgerQueryPort`), and the latest score run's
already-narrated, already-dated actions filtered to this issue's finding
types (`research.md` Decision 4) — generates via the same `LLMPort`/
`GENERATION_MODEL_ID` the Narrator and Ask agent already use, runs five
pure pre-display checks (`app.experience.domain.services.verify_facts`
reusing the Narrator's own `fact_check`, plus four new functions
`verify_dates`/`verify_no_invented_cause`/`verify_no_leak`/
`verify_no_concession` — revised from three to five checks per
`/speckit-analyze` findings G1/U1, 2026-08-16, `research.md` Decision 6),
and persists into `draft_messages` — a
table that has existed, unpopulated, since feature 001's initial migration.
Wires all three already-documented routes (`POST /api/drafts`,
`.../copy`, `.../log-as-sent`) for the first time; `architecture/
07-api-spec.md` has specified their schemas since before this feature
existed, and this feature adds **zero new fields** to any of them — the
first feature since 006 to close a gap with no additive schema change at
all. On the frontend, gives `frontend/src/draft-composer/` (currently
`.gitkeep` only) its first real content, and wires feature 008's `DraftHandoff`
stub (`frontend/src/ask/components/answer-renderer.tsx` — currently static
placeholder text) into a real link that opens it. No send capability is
introduced anywhere, by construction — there is no fourth route to build,
only three, exactly matching `architecture/07-api-spec.md`'s own documented
set (REQ-M10-P1).

## Technical Context

**Language/Version**: Python 3.12 (backend), TypeScript + React 18
(frontend) — unchanged from features 001–008; the second feature since 006
to touch both sides of the stack in one pass.

**Primary Dependencies (new in this feature)**: None. No new Python package
(`anthropic` already adopted since feature 007, reused via the existing
`AnthropicLLMAdapter`, constructed with `settings.generation_model_id`
exactly as the Narrator and Ask agent already do — `research.md` Decision
1). No new frontend package (React/TanStack Query/Tailwind, all already
adopted).

**Storage**: PostgreSQL 16 — **no migration**. `draft_messages` and the
`tone_variant` enum already exist since feature 001's straight-DDL-import
migration (`research.md` Decision 11, confirmed by reading the actual DDL
file, not the prose schema doc alone). This feature is the first real writer
of `draft_messages`, the same status `narrator_outputs`/`ask_queries` had
before feature 008.

**Testing**: pytest + `hypothesis` (backend), Vitest (frontend). All five
check functions (`verify_facts`/`verify_dates`/`verify_no_invented_cause`/
`verify_no_leak`/`verify_no_concession`) are pure and unit-tested directly
against known-good/known-bad `(draft_text, context)` pairs — no DB, no LLM,
mirroring `test_fact_check.py`'s own precedent exactly (`research.md`
Decision 12). `GenerateDraftUseCase` gets `LLMPort` faked in its own test,
matching every prior feature's fake-in-tests precedent. A real-DB/real-route
test exercises `POST /api/drafts` → `/copy` → `/log-as-sent` end to end
against the worked-example fixture, plus a scripted red-team case per check.
A dedicated static-scan test (`research.md` Decision 14) confirms no file
this feature touches imports an outbound-transport client (SC-004). "Draft
quality" itself — specifically blame language (FR-012) and "exactly one
ask" (FR-003), the two properties left prompt-only after `/speckit-analyze`
— stays outside CI scope; `tests/strategy.md` already excludes it
explicitly, deferring to the
production metric "≥ 40% of drafts sent after light editing" (spec §14.2),
the same exclusion already applied to Narrator prose quality.

**Target Platform**: Same Docker Compose stack as features 001–008 — no new
service, no `docker-compose.yml` change, no new `Settings` field, no new env
var. `GENERATION_MODEL_ID` already exists.

**Project Type**: Web application — backend (Python/FastAPI) and frontend
(React/TypeScript) both change. Backend: extended `app.experience.{domain,
application,adapters}` (no new top-level module — M10 lives inside
`experience`, per `decisions/02`), three new routes. Frontend:
`frontend/src/draft-composer/` (currently an empty scaffold, `.gitkeep`
only) gets its first real components; `frontend/src/ask/components/
answer-renderer.tsx`'s existing `DraftHandoff` stub gets a real trigger.

**Performance Goals**: 10s timeout, 1 retry, 2s backoff (~22s worst case) —
already specified for this exact component in `architecture/
06-error-handling.md`, not re-decided here, now actually exercised for the
first time by this feature's own tests. No new performance target; REQ-M10
itself states no hard latency requirement beyond this existing resilience
budget (spec.md SC-001's qualitative "same order of time as opening the
evidence behind it").

**Constraints**: REQ-M10-P1–P6 — structural, not conventions. No `/send`
route exists in `architecture/07-api-spec.md`'s already-ratified contract
and none is added (P1, verified mechanically by `research.md` Decision 14's
transport-import scan, not just by the route table's own absence); five
mechanical checks (`verify_facts`/`verify_dates`/`verify_no_invented_cause`/
`verify_no_leak`/`verify_no_concession`) are the only gate between a
candidate draft and `draft_messages`, matching the Narrator's own
`fact_check()` precedent exactly (P3, P5, P6 — REQ-M10-07, REQ-M10-P3,
REQ-M10-P4); `draft_messages` has no `sent_at`/`sent_by` column, a
schema-level guarantee this feature cannot route around even if application
logic were bypassed. Only REQ-M10-P2 (blame) and FR-003 (exactly one ask)
remain prompt-enforced, not mechanically checked — an explicit, documented
scope boundary re-justified after `/speckit-analyze` (`research.md`
Decision 6), not an oversight: discounts (REQ-M10-P4) and invented causes
(REQ-M10-P3's second half) were the two genuine gaps that analysis found
and this plan now closes.

**Scale/Scope**: Fixture-driven, same as every prior feature — the real,
already-ingested/read/scored/validated/narrated Meridian ledger. Ana (issue
A, ticket #456, confirmed baseline since feature 007) exercises the full
happy path end to end, reproducing `examples/01-end-to-end-walkthrough.md`
§13's `draft-1` row for the first time this codebase has ever generated it.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| **P1 Evidence or It Does Not Exist** | Yes — `evidence_event_ids` is non-empty by `CHECK` constraint (unchanged, existing schema); `verify_facts` is this principle's enforcement layer for *drafted prose*, the exact same role `fact_check` already plays for the Narrator's prose (feature 008) | **Pass** — FR-001, FR-007, FR-013 |
| **P2 The Model Interprets, Code Calculates** | Yes — the draft composer's `LLMPort` call never produces a number; every point value that could appear (none are required by REQ-M10) stays absent from drafted text by construction — nothing here recalculates the score | **Pass** — no arithmetic touched; `.importlinter`'s `scoring-domain-purity` contract is untouched (no code added to `app.scoring`) |
| **P3 Each Component Refuses to Do the Next One's Job** | Yes — the draft composer never re-ranks issues, never re-scores, never composes on the Narrator's behalf; it consumes the Narrator's already-narrated actions (`research.md` Decision 4) rather than re-deriving them | **Pass** — FR-001, FR-018 |
| **P4 A Human Always Sends** | **Yes, directly — this is the feature P4 is written about.** No send capability anywhere, in any form; "Copy draft"/"Log as sent (manual)" are the only two actions; REQ-M10-09's clock-closing happens only after the human sends through their own tool and a collector observes it independently | **Pass** — FR-009, FR-009a, FR-010, FR-011; SC-004 |
| **P5 Admit What We Cannot See** | Yes — a `422` check-failure never looks like a successful, partial draft (`checks_passed` is never `false` on a persisted row, `research.md` Decision 7); `communication_norms: None` on an unseeded profile stays visibly absent, not defaulted to a fabricated style | **Pass** — FR-008; Edge Cases |
| **P6 Silence Is a Success State** | Yes — no draft is ever generated speculatively; generation only happens on an explicit "write to X about this" request, never proactively, and a thin-evidence issue simply produces no draft rather than a manufactured one | **Pass** — Edge Cases |
| **P7 Context Over Sentiment** | Yes — `communication_norms` (rhythm, per-stakeholder style embedded in the account's own free text) drives tone matching, never a generic sentiment scale (REQ-M10-04) | **Pass** — FR-004 |
| **P8 Clean Architecture: the Dependency Rule Is Law** | Yes — all new code lands exactly where the codebase's own established convention already places this shape of work (`experience/application/use_cases.py` + `application/prompts/`, matching `GetDashboardUseCase`/`narration_v1.py`'s own precedent — `research.md` Decision 2); the five domain-level check functions are pure, no I/O; reusing `app.narrator.domain.fact_check` is a `domain`→`domain` cross-module import, a direction `.importlinter`'s `global-dependency-rule` contract does not forbid | **Pass** — `research.md` Decisions 1–3; no `.importlinter` config change needed |
| **P9 Test-First Determinism** | Yes — all five check functions are pure and directly unit-tested with plain asserts, no DB, no LLM, matching `fact_check`'s own precedent; this feature does not touch `backend/app/ledger/` or `backend/app/scoring/`, so golden-replay/monotonicity/reconciliation are unaffected — confirmed, not assumed, by `draft_messages`' deliberate exclusion from the golden-replay snapshot (`research.md` Decision 12, `quickstart.md` step 6) | **Pass — no Complexity Tracking exception** |
| **P10 Simplicity Over Speculative Generality (YAGNI)** | Yes — no new column, no new table, no new orchestration framework for a component `decisions/02` already specified as "a plain `LLMPort` call"; talking points reuse `draft_text` itself rather than a new `is_call` flag (`research.md` Decision 8); tone variants are separate calls, not a speculative `variants[]` array (`research.md` Decision 9) | **Pass** |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | Yes — `frontend/src/draft-composer/` follows the same typed, TanStack-Query, feature-oriented pattern `frontend/src/ask/` already established in feature 008; no ad hoc fetches, no untyped props | **Pass** |
| Full-Stack §4 Testing Strategy | Yes — pure-function unit coverage plus a real-DB/real-route integration test, matching the Narrator's own test shape | **Pass** — see Testing above |
| Full-Stack §5 Security & Quality Gates | Yes — no new external credential; `requested_by_user_id` sourced from the bearer token, never the request body, matching every existing "who did this" column's discipline | **Pass** |

**No violations requiring justification.** This feature closes REQ-M10 with
zero schema changes and zero new dependencies — the smallest-footprint
feature since 001, not a source of new complexity.

**Post-`/speckit-analyze` note (2026-08-16)**: A pre-implementation analysis
pass found nine findings (3 HIGH, 4 MEDIUM, 2 LOW), none CRITICAL — no
Constitution Check row above changed status as a result, but two rows
(P8's check-function count, P9's check-function count) were updated to
reflect the check pipeline growing from three to five functions
(`research.md` Decision 6). Full findings and remediation:
`research.md`'s "Corrections made to `spec.md`" section.

## Project Structure

### Documentation (this feature)

```text
specs/009-draft-composer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output — new ports/value objects, zero migration
├── contracts/
│   └── drafts.md         # Phase 1 output — the three already-documented routes, first implementation
└── quickstart.md         # Phase 1 output — generate, tone-switch, copy/log, red-team check, handoff wiring
```

### Source Code (repository root)

Extends `backend/app/experience/`, substantial since feature 006 and further
extended in feature 008 — following `decisions/02-repo-and-tooling.md`'s
module→package mapping. No new top-level backend package.

```text
backend/
├── app/
│   ├── narrator/
│   │   └── domain/
│   │       ├── entities.py            # unchanged — VerifiedFactSet,
│   │       │                           #   FactCheckResult imported
│   │       │                           #   cross-module (research.md
│   │       │                           #   Decision 2), not redefined
│   │       └── services.py            # unchanged — fact_check() imported
│   │                                   #   cross-module, not redefined
│   ├── experience/
│   │   ├── domain/
│   │   │   ├── entities.py            # extended: IssueEvidenceRecord,
│   │   │   │                           #   AgreedAction, VerifiedDateSet,
│   │   │   │                           #   DateCheckResult, CauseCheckResult,
│   │   │   │                           #   LeakCheckResult,
│   │   │   │                           #   ConcessionCheckResult,
│   │   │   │                           #   DraftCheckResult, GeneratedDraft
│   │   │   │                           #   (5-check set, /speckit-analyze
│   │   │   │                           #   findings G1/U1, 2026-08-16)
│   │   │   └── services.py            # extended: verify_facts (thin
│   │   │                               #   wrapper over app.narrator's
│   │   │                               #   fact_check), verify_dates,
│   │   │                               #   verify_no_invented_cause,
│   │   │                               #   verify_no_leak,
│   │   │                               #   verify_no_concession — all pure,
│   │   │                               #   no I/O (research.md Decision 6)
│   │   ├── application/
│   │   │   ├── ports.py               # extended: IssueReadPort,
│   │   │   │                           #   PlaybookReadPort,
│   │   │   │                           #   DraftMessageRepositoryPort;
│   │   │   │                           #   ClientProfileRecord gains
│   │   │   │                           #   communication_norms;
│   │   │   │                           #   StakeholderReadPort gains get()
│   │   │   │                           #   (research.md Decision 13)
│   │   │   ├── use_cases.py           # extended: GenerateDraftUseCase,
│   │   │   │                           #   alongside GetDashboardUseCase/
│   │   │   │                           #   GetEvidenceTraceUseCase/
│   │   │   │                           #   GetCoverageUseCase (existing
│   │   │   │                           #   file, established pattern)
│   │   │   └── prompts/
│   │   │       └── draft_composer_v1.py  # NEW: versioned structured-output
│   │   │                                   #   prompt template (REQ-M10's
│   │   │                                   #   analog of REQ-M7-08) — lives
│   │   │                                   #   in application/, matching
│   │   │                                   #   narration_v1.py's own
│   │   │                                   #   precedent (feature 008 T040)
│   │   └── adapters/
│   │       ├── draft_router.py        # NEW: POST /api/drafts,
│   │       │                           #   .../copy, .../log-as-sent —
│   │       │                           #   composition root, constructs
│   │       │                           #   AnthropicLLMAdapter, matching
│   │       │                           #   ask_router.py's existing pattern
│   │       └── sqlalchemy_repository.py  # extended: SqlAlchemyIssueReader,
│   │                                       #   SqlAlchemyPlaybookReader,
│   │                                       #   SqlAlchemyDraftMessageRepository;
│   │                                       #   SqlAlchemyClientProfileRepository
│   │                                       #   gains communication_norms read;
│   │                                       #   SqlAlchemyStakeholderReader
│   │                                       #   (feature 008) gains get()
│   │                                       #   (research.md Decision 13)
│   └── main.py                        # extended: registers draft_router
└── tests/
    └── experience/
        ├── test_draft_checks.py       # NEW — pure, no DB, no LLM: all
        │                               #   five check functions'
        │                               #   known-good/known-bad pairs
        ├── test_generate_draft_use_case.py  # NEW — LLMPort faked, incl.
        │                                     #   the stakeholder-404 case
        ├── test_draft_routes_real_db.py     # NEW — real-DB integration:
        │                                     #   generate → copy →
        │                                     #   log-as-sent, a 404 probe
        │                                     #   against /send, and one
        │                                     #   red-team case per check
        └── test_no_external_transport.py    # NEW — static scan: no file
                                               #   this feature touches
                                               #   imports an outbound-
                                               #   transport client
                                               #   (research.md Decision 14,
                                               #   /speckit-analyze G2)

frontend/
└── src/
    ├── ask/
    │   └── components/
    │       └── answer-renderer.tsx    # extended: DraftHandoff gets a
    │                                   #   real link (research.md
    │                                   #   Decision 10), replacing the
    │                                   #   static placeholder text
    └── draft-composer/                 # currently .gitkeep only
        ├── draft-composer-panel.tsx   # NEW: opens beside the evidence,
        │                               #   tone-variant tabs, Copy/Log
        │                               #   actions, no edit control
        ├── draft-composer-panel.test.tsx  # NEW
        ├── api.ts                     # NEW: POST /api/drafts +
        │                               #   /copy + /log-as-sent client
        └── types.ts                   # NEW: DraftRequest, DraftResponse,
                                         #   ToneVariant

architecture/07-api-spec.md             # unchanged — this feature adds no
                                          #   new field to any documented
                                          #   schema (data-model.md)
data-base/08-schema-experience.md       # unchanged — no schema change
```

**Structure Decision**: Same monorepo, extending `experience/` — the module
`decisions/02-repo-and-tooling.md` already assigns M10 to — with real code
for the first time. No new top-level backend directory, no new Docker
service, no new outbound dependency. On the frontend, `frontend/src/
draft-composer/` — an empty scaffold since before this feature — gets its
first real content; no new top-level frontend directory. One of the
smallest source-tree footprints of any feature since 001: one new router
file, one new prompt-template file, a handful of extended existing files
(`entities.py`, `services.py`, `ports.py`, `use_cases.py`,
`sqlalchemy_repository.py`), and zero migrations — the five-check pipeline
(`research.md` Decision 6) adds more functions than routes or tables.

## Complexity Tracking

> No violations requiring justification — see Constitution Check above. This
> feature adds no new dependency, no new table, no new top-level module, and
> no new Complexity Tracking exception of its own.

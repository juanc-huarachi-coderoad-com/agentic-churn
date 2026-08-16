# Implementation Plan: Model Findings

**Branch**: `007-model-findings` | **Date**: 2026-08-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/007-model-findings/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Fill in the three empty stubs feature 005 scaffolded for this feature —
`backend/app/readers/application/{tone,intent}_reader.py`,
`.../validation_gate.py` — with real code: the Tone reader (baseline-relative
deviation, LLM), the Intent reader (closed-enum escalation/competitive/
contractual classification, LLM), and the M5a validation gate (four checks,
wired against **all eight** reader types, not just these two). Technical
approach: build `LLMPort`/`AnthropicLLMAdapter` into `app.readers.{application,
adapters}` at the exact location `decisions/02-repo-and-tooling.md` already
ratifies (not a new decision this feature makes); extend `RunReadersUseCase`
(feature 005) so every finding passes through `ValidationGate` before its one
and only `persist()` call, replacing the current unconditional `pending_
validation` write; add a small `app.readers.domain` ring (this module's first
real domain logic — value objects for the gate's decision and Tone's baseline
input) following feature 005/006's established "domain ring appears once a
module has genuine pure logic to isolate" pattern; seed two new
`finding_type_config` rows for Intent's previously-unseeded categories
(Clarifications); add a `scripts/confirm_baseline.py` manual trigger,
mirroring `scripts/run_readers.py`/`compute_score.py`'s existing pattern,
since `baseline_confirmations` has no writer anywhere in the codebase yet and
no Post-MVP Profile Editor UI exists to build one into. No new HTTP route, no
frontend change — `GET /api/coverage`'s `quarantine` field (feature 006)
already exists and simply starts returning real rows.

## Technical Context

**Language/Version**: Python 3.12 (backend) — unchanged from features 001–006

**Primary Dependencies (new in this feature)**: `anthropic` (Tone/Intent
readers' `AnthropicLLMAdapter`, `claude-haiku-4-5-20251001` via
`READER_MODEL_ID` — `decisions/02-repo-and-tooling.md`, already an adopted-
stack dependency per the constitution, first feature to actually import it,
mirroring how feature 005 was the first to actually import the already-
adopted `openai`). Confined to `app.readers.adapters` —
`.importlinter`'s existing `readers-application-purity` contract already
forbids `anthropic` in `app.readers.application`/`domain`, enforced without a
config change (same contract feature 005 already relies on for `openai`).

**Storage**: PostgreSQL 16 — no new tables, no migration. `findings`,
`quarantine`, `quarantine_reasons`, `finding_type_config`
(`data-base/05-schema-reasoning.md`) and `baseline_confirmations`
(`data-base/03-schema-ledger.md`) all already exist from feature 001's
migration; this feature is the first real writer of `quarantine`/
`quarantine_reasons`/`baseline_confirmations`, and the first to write
`findings.status` values other than `pending_validation`. Two new rows are
added to `data-base/11-seed-data.sql`'s existing `finding_type_config`
`INSERT` (`research.md` Decision 7) — a data change, not a schema change.

**Testing**: pytest + `hypothesis` — per-reader unit tests with `LLMPort`
faked (a fake returning fixed structured responses for known prompts, no live
Anthropic call in the suite — matches `EmbeddingPort`'s existing fake-in-
tests precedent, `architecture/08-class-diagrams.md`'s golden-replay design);
`ValidationGate` unit tests, pure, no DB, covering all four checks
individually and in combination (a finding failing two checks at once);
a real-DB integration test extending `test_run_readers_use_case.py`
(feature 005) to assert `validated`/`quarantined` outcomes instead of the
current blanket `pending_validation` assertion (`specs/ROADMAP.md`'s feature
006 log entry already flagged this exact assertion as needing to change);
two new small JSON fixtures (`tests/fixtures/tone_baseline_sufficient.json`,
`tests/fixtures/tone_low_confidence.json`) since the real Meridian fixture is
deliberately too small to clear REQ-M6-CAL-04's 5-message floor
(`quickstart.md` step 2 — proving that abstention honestly, not hiding it).

**Target Platform**: Same Docker Compose stack as features 001–006 — no new
service, no `docker-compose.yml` change (every service already loads
`env_file: .env`; the two new env vars need no new wiring, only new
`Settings` fields in `backend/app/config.py` and new entries in
`.env.example`, which currently has neither `ANTHROPIC_API_KEY` nor the
pre-existing `OPENAI_API_KEY` — the latter a pre-existing gap from feature
005 this feature does not need to fix, but should not compound).

**Project Type**: Backend-only for this feature — no frontend work, no new
HTTP route (`spec.md`'s own scope boundary; `GET /api/coverage`'s existing
`quarantine` field, feature 006, simply starts returning real data).

**Performance Goals**: Tone/Intent's 8s-per-attempt, 2-retry budget
(`architecture/06-error-handling.md`, already specified, not re-decided
here) keeps the pipeline inside REQ-NFR-02's 60s hard ceiling; not directly
measured in this feature since reader triggering stays manual
(`spec.md`'s Assumptions, matching feature 005's own "manual trigger script,
no live event-driven path" scope boundary) — the live-trigger path this
budget protects doesn't exist as a caller yet.

**Constraints**: REQ-M5-P2/P3/P4 — Tone/Intent hold zero tools, zero side
effects, and no trigger path may bypass the gate, all structural properties
of `LLMPort.generate_structured(prompt, schema)`'s signature (no `tools`
parameter exists on this interface, `architecture/09`) and of
`RunReadersUseCase`'s new synchronous gate wiring (`research.md` Decision 5)
applying uniformly to every registered reader, no urgency-based branch;
REQ-M5A-03 — `quarantine.finding_id` stays `UNIQUE`, enforced at the schema
level since feature 001, no new enforcement needed; `.importlinter`'s
`readers-application-purity` contract — no `anthropic` import outside
`app.readers.adapters`.

**Scale/Scope**: Fixture-driven for this feature, same as 004/005/006 — the
real, already-ingested Meridian ledger plus two new small synthetic fixtures
for the two baseline-dependent test cases the real fixture can't exercise
(too few historical Ana messages) — REQ-NFR's ~50k–200k events/year
production scale remains a later concern.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Applies to this feature? | Status |
|---|---|---|
| **P1 Evidence or It Does Not Exist** | Yes — Tone/Intent findings cite real event IDs like every other reader; the gate's `cited_event_missing` check is this principle's second, independent enforcement layer beyond the existing DB `CHECK` | **Pass** — FR-006, FR-008 |
| **P2 The Model Interprets, Code Calculates** | Yes — `LLMPort.generate_structured` returns `{deviation/category, magnitude, confidence, cited_event_ids}`, never a number the gate or scoring engine trusts as-is without its own arithmetic; the gate's four checks are plain code, no model call | **Pass** — REQ-M5-12, FR-004; `.importlinter`'s `scoring-domain-purity` contract is untouched by this feature (readers, not scoring, is where the LLM call lives) |
| **P3 Each Component Refuses to Do the Next One's Job** | Yes — Tone/Intent interpret, never rank (REQ-M5-P1, unchanged); the gate validates, never repairs (REQ-M5A-03); neither reader is handed anything resembling a scoring or ranking responsibility | **Pass** — FR-011, FR-013 |
| **P4 A Human Always Sends** | No send capability touched | N/A |
| **P5 Admit What We Cannot See** | Yes — a quarantined finding (an observation the system couldn't fully trust) is now visibly distinct from a validated one, not silently dropped or blended in; this is P5's principle applied to reader/finding trustworthiness rather than data-source completeness (corrected from an earlier N/A during `/speckit-analyze` — the underlying behavior was always compliant, only the classification was off) | **Pass** — FR-010, FR-012, SC-004; the degraded-state *mechanics* (timeout→abstain, gate failure→quarantine) are `architecture/06-error-handling.md`'s existing spec, not re-decided here, but making that state visible is this feature's own doing (`quarantine` real for the first time) |
| **P6 Silence Is a Success State** | Yes — Tone abstains below 5 baseline samples (REQ-M6-CAL-04) rather than manufacturing a low-confidence finding, and Intent emits nothing for neutral text | **Pass** — FR-002, User Story 1/2 acceptance scenarios |
| **P7 Context Over Sentiment** | Yes — this is the feature that actually builds P7's named example ("The Tone reader compares against a specific stakeholder's own baseline, never a generic sentiment scale") | **Pass** — FR-001, `research.md` Decision 2 |
| **P8 Clean Architecture: the Dependency Rule Is Law** | Yes — `readers/{domain,application,adapters}` gains its first real `domain/` ring (value objects only, no I/O); `LLMPort`/`AnthropicLLMAdapter` sit exactly where `decisions/02-repo-and-tooling.md` already assigns them, not a new architectural choice | **Pass** — `.importlinter`'s `readers-application-purity` and `global-dependency-rule` contracts already cover `app.readers`; no config change needed |
| **P9 Test-First Determinism** | Partially — `ValidationGate`'s four checks are deterministic and fully unit-testable with plain values (no DB, no LLM); the LLM call itself is inherently non-deterministic, isolated behind `LLMPort` and faked in every test that isn't the manual quickstart | **Pass, with the same noted exception features 004/005 already recorded** — see Complexity Tracking (golden-replay stays skipped, needs Narrator/feature 008) |
| **P10 Simplicity Over Speculative Generality (YAGNI)** | Yes — Tone's baseline input is raw message text via a small reader-owned port, not a new general-purpose rollup metric (`research.md` Decision 2); `baseline_confirmations` gets a manual script, not a speculative API/UI ahead of the Post-MVP Profile Editor (`research.md` Decision 3); the gate is four fixed methods, not a `Specification`-object framework (already the constitution's own named example) | **Pass** |
| P11 Frontend: Feature-Oriented, Typed, Spec-Driven | N/A — no frontend surface in this feature | N/A |
| Full-Stack §4 Testing Strategy | Yes — Tone/Intent/gate each need dedicated unit coverage plus one real-DB integration test | **Pass** — see Testing above; `tasks.md` assigns one test file per new component |
| Full-Stack §5 Security & Quality Gates | Yes — `ANTHROPIC_API_KEY` is a new external-service credential | **Pass** — read from environment/config the same way `OPENAI_API_KEY` already is (feature 005's precedent), never logged or persisted |

**No violations requiring justification beyond the one already-established
golden-replay exception.** Complexity Tracking table below records it, not a
new one.

## Project Structure

### Documentation (this feature)

```text
specs/007-model-findings/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output — new ports/value objects, gate wiring, seed data
└── quickstart.md         # Phase 1 output — run readers, confirm baseline, verify gate + dashboard
```

No `contracts/` directory — this feature adds no new API route or external
interface (`spec.md`'s own scope boundary: `GET /api/coverage`'s contract
already exists, feature 006). Matches the plan template's own guidance to
skip contracts for a purely internal component, same as feature 005.

### Source Code (repository root)

Fills in `backend/app/readers/`, already scaffolded by feature 001/005 —
following `architecture/09-clean-architecture-and-patterns.md`'s file layout
and `architecture/08-class-diagrams.md`'s named `Reader` subclass catalog:

```text
backend/
├── app/
│   ├── readers/
│   │   ├── domain/
│   │   │   ├── entities.py            # extended: ValidationGateResult,
│   │   │   │                           #   FailedCheck, ConfirmedBaselineWindow
│   │   │   │                           #   — this module's first real domain
│   │   │   │                           #   ring (pure value objects, no I/O)
│   │   │   └── services.py            # NEW: the gate's four check functions,
│   │   │                               #   pure — schema_valid, cited_events_
│   │   │                               #   exist, sufficient_evidence,
│   │   │                               #   confidence_at_floor
│   │   ├── application/
│   │   │   ├── ports.py               # extended: LLMPort, MessageEvent
│   │   │   │                           #   RepositoryPort (shared candidate-
│   │   │   │                           #   message corpus, Foundational — both
│   │   │   │                           #   Tone and Intent read it),
│   │   │   │                           #   ConfirmedBaselineRepositoryPort,
│   │   │   │                           #   FindingTypeConfigPort,
│   │   │   │                           #   EventExistencePort,
│   │   │   │                           #   QuarantineRepositoryPort
│   │   │   ├── tone_reader.py         # ToneReader.interpret() — fills feature
│   │   │   │                           #   005's empty stub
│   │   │   ├── intent_reader.py       # IntentReader.interpret() — fills
│   │   │   │                           #   feature 005's empty stub
│   │   │   ├── validation_gate.py     # ValidationGate — fills feature 005's
│   │   │   │                           #   empty stub; orchestrates domain/
│   │   │   │                           #   services.py's four checks
│   │   │   └── use_cases.py           # extended: RunReadersUseCase now calls
│   │   │                               #   ValidationGate.evaluate() per
│   │   │                               #   finding before its one persist()
│   │   │                               #   call (research.md Decision 5)
│   │   └── adapters/
│   │       ├── anthropic_llm.py       # NEW: AnthropicLLMAdapter (implements
│   │       │                           #   LLMPort) — the only file in this
│   │       │                           #   module importing `anthropic`
│   │       └── sqlalchemy_repository.py  # extended: SqlAlchemyMessageEvent
│   │                                    #   Repository, SqlAlchemyConfirmedBaseline
│   │                                    #   Repository, SqlAlchemyFindingTypeConfig
│   │                                    #   Repository, SqlAlchemyEventExistence
│   │                                    #   Repository, SqlAlchemyQuarantine
│   │                                    #   Repository
│   └── config.py                      # extended: anthropic_api_key,
│                                        #   reader_model_id settings fields
├── scripts/
│   └── confirm_baseline.py            # NEW: manual baseline-confirmation
│                                        #   trigger, mirrors run_readers.py/
│                                        #   compute_score.py's pattern
└── tests/
    ├── readers/
    │   ├── test_tone_reader.py        # LLMPort faked, no live API call
    │   ├── test_intent_reader.py      # LLMPort faked, no live API call
    │   ├── test_validation_gate.py    # pure, no DB — all four checks,
    │   │                               #   individually and combined
    │   └── test_run_readers_use_case.py  # extended: real-DB integration —
    │                                       #   asserts validated/quarantined
    │                                       #   outcomes (replaces feature
    │                                       #   005's blanket pending_
    │                                       #   validation assertion)
    └── fixtures/
        ├── tone_baseline_sufficient.json  # NEW — synthetic 5+ prior message
        │                                    #   baseline plus one deviating
        │                                    #   message (quickstart.md step 3)
        └── tone_low_confidence.json       # NEW — synthetic case producing a
                                             #   confidence below the floor
                                             #   (quickstart.md step 5)

.env.example                            # extended: ANTHROPIC_API_KEY,
                                          #   READER_MODEL_ID
data-base/11-seed-data.sql              # extended: 2 new finding_type_config
                                          #   rows (competitive_mention,
                                          #   contractual_reference)
```

**Structure Decision**: Same monorepo, filling in `readers/` — the module
folder feature 005 already scaffolded, including this feature's three named
stub files — with real code for the first time. `app.readers/domain/` gains
its first content (feature 005 left it with only re-exported entities, no
module-owned domain logic yet). No new top-level directories, no new Docker
service, no new external port exposed — only a new outbound dependency
(Anthropic's API) from the existing `api` process, alongside the `openai`
dependency feature 005 already introduced.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|---------------------------------------|
| `tests/golden_replay/test_placeholder.py` stays `@pytest.mark.skip` for this feature, in tension with the constitution's Governance clause requiring "a passing golden-replay run before merge" for any PR touching `backend/app/ledger/` or `backend/app/scoring/` (this feature touches neither directly, but the same spirit — full-pipeline determinism — applies to `backend/app/readers/`, which it does touch) | That test's own documented procedure (`tests/strategy.md`) requires the full ledger → readers → score → **Narrator** chain; Narrator (M7, feature 008) still doesn't exist. This feature gets the pipeline one module closer (ledger → readers, now including Tone/Intent → gate → score all real) but still can't flip this specific test green | Same reasoning features 004 and 005 already recorded, extended one feature further: this feature substitutes its own real, scoped determinism guarantee — `test_validation_gate.py` asserts the same finding, re-evaluated by the gate twice, produces an identical decision (no hidden state, no LLM call inside the gate itself), and `test_run_readers_use_case.py`'s existing REQ-M5-15 cache assertion (feature 005) is extended to cover Tone/Intent too. Expected to go green naturally once feature 008 lands |

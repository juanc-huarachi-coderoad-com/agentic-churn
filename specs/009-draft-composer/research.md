# Phase 0 Research: Draft Composer

No `[NEEDS CLARIFICATION]` markers remain in `spec.md` — all three questions
found during `/speckit-clarify` are already resolved there. This document
covers technical decisions the spec deliberately left to planning, surfaced by
reading the actual current state of the codebase (not just the docs) before
writing `tasks.md`.

## Correction made to `spec.md` during this phase

Already applied to `spec.md`'s Clarifications section, recorded here for the
record, matching `specs/007-model-findings/research.md` and
`specs/008-narrator-and-ask-agent/research.md`'s own precedent of surfacing
corrections transparently rather than silently.

1. **The "any issue" clarification's supporting claim.** The clarification
   session justified "accept any issue with cited evidence" partly by saying
   feature 008's `draft_handoff` "carries whatever issue was in context when
   the CS lead said 'write to X about this.'" Reading the actual shipped code
   (`backend/app/experience/adapters/ask_agent_graph.py`'s `handoff()` node,
   lines 387–399) shows this is inaccurate: it always calls
   `toolkit.query_score_runs("top_risk")` and takes the first contribution's
   `issue_id` — today's only caller always passes the top-ranked issue,
   never an arbitrary one. The underlying decision (`DraftRequest.issue_id`
   is a generic, unconstrained contract parameter this feature must not
   hard-restrict to top-rank-only) is still correct and remains unchanged —
   only the inaccurate supporting claim was corrected in place.
2. **`/speckit-analyze` remediation (2026-08-16).** Nine findings — 3 HIGH
   (G1: SC-003's discount/blame guarantee had zero task coverage; U1: REQ-
   M10-P3's "invented causes" half was completely unaddressed; G2: SC-004's
   "code-level review" had no mechanical task), 4 MEDIUM (G3: FR-017 had no
   task-visible rationale; U2: "exactly one ask" has no mechanical check,
   now explicitly documented as intentional; U3: no port checked
   `stakeholder_id` existence; I1: SC-006 overclaimed what independently-
   generated tone variants can guarantee), 2 LOW (I2: `DraftCheckFailedError`
   undocumented in `data-model.md`; A1: SC-001's qualitative timing wording,
   accepted, matches sibling precedent). All addressed below: Decision 6
   revised to five checks (adds `verify_no_invented_cause`,
   `verify_no_concession`); Decision 13 adds the stakeholder check; Decision
   14 adds the mechanical transport-import scan; `spec.md`
   FR-003/FR-013/FR-014/SC-003/SC-004/SC-006 and the Assumptions/Edge Cases
   sections updated to match.

## Decision 1 — `LLMPort` source and model instance

**Decision**: Reuse `LLMPort` from `app.readers.application.ports`, unchanged
— no new interface. Construct a new `AnthropicLLMAdapter` instance with
`settings.generation_model_id` (`claude-sonnet-5`), the same config value and
pattern the Narrator and Ask agent's `classify_intent` step already use
(`specs/008-narrator-and-ask-agent/research.md` Decision 1). No new
`Settings` field, no new env var — `GENERATION_MODEL_ID` already exists.

**Rationale**: `specs/007-model-findings/research.md` Decision 1 explicitly
named this feature as a future `LLMPort` consumer;
`decisions/02-repo-and-tooling.md`'s Claude model ID pinning table already
lists "Narrator / Ask agent / Draft composer" together under
`GENERATION_MODEL_ID`. This is the third call site constructed this way, not
a new pattern.

**Alternatives considered**: A dedicated `DraftGenerationPort` — rejected as
needless duplication of a one-method interface with no module-specific shape
to justify a copy (same reasoning `specs/008-.../research.md` Decision 1
already used to reject this for the Narrator).

## Decision 2 — Module layout

**Decision**: `GenerateDraftUseCase` lives in
`backend/app/experience/application/use_cases.py` — a plain `LLMPort` call,
no orchestration framework — extending the file that already holds
`GetDashboardUseCase`/`GetEvidenceTraceUseCase`/`GetCoverageUseCase`
(feature 006/008 real use-case classes, not a new pattern). The versioned
structured-output prompt template (`DraftComposerPromptV1`, REQ-M10 analog
of REQ-M7-08) lives in `backend/app/experience/application/prompts/
draft_composer_v1.py`, matching `app.narrator.application.prompts.
narration_v1`'s own precedent exactly. `backend/app/experience/adapters/
draft_router.py` is the composition root — constructs `AnthropicLLMAdapter`
with `settings.generation_model_id`, matching `ask_router.py`'s established
pattern — not a separate `draft_composer.py` adapter file. New ports
(`IssueReadPort`, `PlaybookReadPort`, `DraftMessageRepositoryPort`) join the
existing `app.experience.application.ports`. Three new pure functions —
`verify_facts`, `verify_dates`, `verify_no_leak` — are added to the existing
`app.experience.domain.services` module (not a new `domain/` package;
`experience/domain` already exists since feature 006). `verify_facts` reuses
`app.narrator.domain.services.fact_check` and `VerifiedFactSet`/
`FactCheckResult` directly (cross-module import), rather than duplicating the
identical numbers/names extraction logic.

**Rationale**: `decisions/02-repo-and-tooling.md`'s module→package mapping
names the *behavior* correctly — M10 is "a plain `LLMPort` call, no
orchestration framework" — but its literal filenames (`dashboard.py`,
`draft_composer.py`) predate the codebase's own established convention,
found by reading the real tree rather than trusting the doc alone: M8's
actual file is `dashboard_router.py`, and its use case
(`GetDashboardUseCase`) already lives in `application/use_cases.py`, not in
`adapters/dashboard.py`. This feature follows the *real*, already-shipped
convention (`*_router.py` for routes, use cases in `application/use_cases.py`,
prompts in `application/prompts/`) over the doc's slightly stale literal
filename — the same "verify against actual code, not just the prose"
discipline `research.md` Decision 11 applies to the DDL. Reusing
`fact_check`/`VerifiedFactSet` mirrors this repo's own
precedent for `LLMPort` itself (a cross-module import from one module's
`application` layer, here from one module's `domain` layer, where two
modules genuinely need the identical pure logic — same numbers/names
extraction, same "must already exist in the verified set" rule REQ-M7-06 and
REQ-M10-07 share word for word).

**Alternatives considered**: A new top-level `app.drafts` module — rejected,
contradicts the already-ratified mapping and fragments M8/M9/M10, which
`decisions/02` deliberately groups under one `experience` package.
Duplicating `fact_check` inside `experience/domain/services.py` — rejected as
needless duplication of identical logic; the two modules already share
`LLMPort` this way, and `.importlinter`'s `global-dependency-rule` contract
poses no obstacle to a `domain`→`domain` import across modules (only
`adapters`→`application`/`domain` and same-module `application`→`adapters`
are the forbidden directions).

## Decision 3 — "Any issue with cited evidence" needs a new read path

**Decision**: A new `IssueReadPort.get_issue_evidence(issue_id) ->
IssueEvidenceRecord | None` on `app.experience.application.ports`, backed by
a `SqlAlchemyIssueReader` joining `issues` → `finding_issue_map` →
`findings` (`WHERE status = 'validated'`, matching `FindingReadPort.
get_finding`'s existing validated-only filter, feature 007's
`/speckit-analyze` C1 precedent) to return the issue's `label`, the distinct
`finding_types` among its findings, and the aggregated `cited_event_ids`
across all of them.

**Rationale**: No existing port returns "an issue's own evidence" — feature
006's evidence trace is scoped per-`finding_id` (`GET /api/evidence/{id}`),
and `ScoreReadPort.list_contributions` returns per-run contributions with an
`issue_id` field but no aggregation by issue. Since the clarified scope is
"any issue with cited evidence," not only the run's top issue,
`app.narrator.application.ports.ScoreContextPort.get_top_issue` (which only
ever returns the single most impactful issue) cannot serve this feature's
needs unmodified, and modifying a Narrator-owned port to accept an arbitrary
ID would blur that module's own boundary. A new, narrowly-scoped port in the
module that actually owns this feature (`experience`) is the smaller change.

**Alternatives considered**: Extending `ScoreContextPort.get_top_issue` to
take an optional `issue_id` — rejected; that port is Narrator-owned
(`app.narrator.application.ports`) and scoped to "the run's top issue" by
name and by every existing caller; repurposing it here would make a
Narrator-specific port do double duty for an unrelated module, the exact
shape of coupling P3 ("each component refuses to do the next one's job")
warns against.

## Decision 4 — "Actions the team has actually agreed to" (REQ-M10-01's 4th input)

**Decision**: Reuse the latest score run's `narrator_outputs.actions`
(`NarratorReadPort.get_latest()`, already built in feature 008), filtered to
the entries whose `playbook_id` resolves to one of the target issue's own
`finding_types`. A new `PlaybookReadPort.finding_type_for_playbook(playbook_id)
-> str | None` (`SELECT applies_to_finding_type FROM playbook_actions WHERE
id = :id`) does the resolution — a small, single-purpose lookup, not a
duplicate of `app.narrator.application.ports.PlaybookPort` (which lists
templates by finding type, the reverse direction).

**Rationale**: `narrator_outputs.actions`' JSONB shape (`{text, owner,
due_date, playbook_id}`, `data-base/08-schema-experience.md`) carries no
`finding_type`/`issue_id` of its own — the Narrator's actions span the whole
run, not one issue. Filtering by the matched playbook template's
`applies_to_finding_type` is the only existing link back to a finding type,
and finding type is what an issue's own findings carry (`FindingRecord.
finding_type`, already read via `IssueReadPort.get_issue_evidence`).
Reusing already-narrated, already-fact-checked, already-dated actions (rather
than re-deriving action candidates from scratch) is also what makes
REQ-M10-07's "no dated promise unless a human supplied that date" check
tractable: an action's `due_date` is human-owned by construction — it came
from `playbook_actions.default_sla_days`/a CS lead's own edit, never invented
by the Narrator's own fact-check-gated generation.

**Alternatives considered**: Re-deriving candidate actions directly from
`playbook_actions` inside the Draft composer, independent of the Narrator's
run — rejected; it would duplicate REQ-M7-04/05's "personalize from the
fixed playbook, always with an owner and a date" discipline instead of
reusing output that already satisfies it, and could disagree with what the
dashboard already shows for the same run.

## Decision 5 — Thread history and communication norms: no new read paths

**Decision**: "Real thread history" (REQ-M10-01) reuses
`LedgerQueryPort.timeline_for_stakeholder(stakeholder_id)`, already built in
feature 008 for the Ask agent's "show me everything about X" intent — no new
port. Communication norms reuse `ClientProfileRepositoryPort.get_current()`,
extended with one additive field: `communication_norms: str | None` on
`ClientProfileRecord` (currently `client_name`/`renewal_date` only).

**Rationale**: `timeline_for_stakeholder` already returns exactly what's
needed — every message-bearing event for a stakeholder, most recent first —
with no draft-composer-specific shape required. The `ClientProfileRecord`
extension mirrors feature 006's own precedent adding `renewal_date` to the
same record (`/speckit-analyze` finding CV2) — an additive field on an
already-owned port, not a new one. `communication_norms` is one free-text
field for the whole account (`data-base/04-schema-context.md`), not a
structured per-stakeholder field; per-person guidance ("Ana is direct,
prefers short messages," the worked example's own wording,
`examples/01-end-to-end-walkthrough.md` §13) is expected to already be
written into that text by the CS lead, and the generation prompt passes the
whole text plus the target stakeholder's name, letting the model apply
whatever's relevant — matching REQ-M3-04's "supplied ... as context only."

**Alternatives considered**: A new structured per-stakeholder
`communication_style` field — rejected; would be a real schema change
(new column, new migration) for a shape REQ-M3-01's already-ratified profile
fields don't include, and P10 (YAGNI) counsels against introducing a
structured taxonomy the product has never asked for.

## Decision 6 — Pre-display checks: five pure functions (revised,
`/speckit-analyze` findings G1/U1, 2026-08-16)

**Decision**: `app.experience.domain.services` gains five pure functions,
composed by the use case into one `DraftCheckResult`:

1. `verify_facts` — reuses `app.narrator.domain.services.fact_check`/
   `VerifiedFactSet` verbatim (Decision 2) against a fact set built from the
   issue's cited evidence + thread history + client profile.
2. `verify_dates` — extracts date-like tokens (weekday names, month names,
   explicit dates — deliberately the same tokens `fact_check`'s own
   `_COMMON_WORDS` list excludes from the generic name-check, since dates
   need a different verification rule than names) and confirms each one
   matches a `due_date` from the matched actions (Decision 4) or an
   existing `response_pairs`/`commitments` record — never passes an
   unmatched date.
3. `verify_no_invented_cause` — **new** (`/speckit-analyze` finding U1):
   extracts every sentence containing a causal connective (`because`,
   `due to`, `since`, `as a result of`, `given that` — a closed, small set
   deliberately kept narrow to bound false positives) and, for the clause
   following the connective, reuses `extract_numbers_and_names`
   (Decision 2's imported function) to confirm every number/name in that
   clause exists in the same `VerifiedFactSet` `verify_facts` already
   builds — an invented cause almost always names an entity, product, or
   number the evidence doesn't support, and this reuses the exact
   extraction/verification logic already proven for `verify_facts`, scoped
   to causal clauses specifically rather than the whole sentence.
4. `verify_no_leak` — a closed denylist of internal-only terms (`score`,
   `risk`, `monitoring`, `quarantine`, `churn`, `damping`, `band`, and
   case-insensitive variants — matching
   `requirements/10-draft-composer.md`'s own acceptance criterion wording
   verbatim) plus a check that no stakeholder/client name outside the
   current profile appears in the text.
5. `verify_no_concession` — **new** (`/speckit-analyze` finding G1): a
   closed, case-insensitive denylist of commercial-concession terms
   (`discount`, `% off`, `waive`, `credit your account`, `complimentary`,
   `free month`, `refund` — REQ-M10-P4). Deliberately narrower in scope
   than a general "no concession" semantic check — a fixed term list, the
   same shape of check `verify_no_leak` already uses successfully.

**Scope boundary, stated explicitly and re-justified after
`/speckit-analyze`**: REQ-M10-P2 (no blame language) and FR-003 (exactly
one ask) remain prompt-enforced only, not mechanically checked — the two
places where a keyword/pattern-based check's false-positive rate would be
worst: "sorry for the friction" is a genuine apology, not blame, and
"exactly one ask" requires actual intent parsing, not a pattern. Discount
language and invented causes, unlike blame, are specific enough
(closed commercial-term vocabulary; causal connectives + the same
name/number extraction already proven for facts) to check reliably at low
false-positive cost — that asymmetry is exactly why this decision now
covers five checks instead of three, not four or six.

**Rationale**: Closes the two real, `/speckit-analyze`-identified gaps
(G1's discount half, U1's invented-cause half) using the same pure,
independently-testable, no-I/O pattern `fact_check` already established,
without over-reaching into genuinely unreliable detection (blame,
one-ask-counting) where a false positive would block a legitimate,
truthful draft.

**Alternatives considered**: A single monolithic `verify_draft` function —
rejected, same reasoning as before: five small, independently
unit-testable functions match `fact_check`'s own "pure, no I/O, testable
with plain asserts" precedent. Mechanically detecting blame via a keyword
denylist — rejected for the same reason as before: "sorry"/"unfortunately"
style words appear in genuine, non-blaming apologies far more often than in
actual blame, an asymmetry discount/cause terms don't share (a discount
term appearing in quoted client text is a real, accepted edge case,
narrower and rarer than the blame false-positive rate). A generic causal-
language NLP classifier for `verify_no_invented_cause` — rejected;
YAGNI (P10) for a problem the same numbers/names extraction already
mostly solves once scoped to the clause following a causal connective.

## Decision 7 — Check-failure transport: HTTP 422, no new schema

**Decision**: `POST /api/drafts` returns `422` with `ErrorResponse{detail:
str}` when any of the checks fails (three at the time this decision was
first written; five after `/speckit-analyze`'s Decision 6 revision,
2026-08-16 — this decision's transport mechanism is unaffected by how many
checks compose `DraftCheckResult`) — `detail` is always the same
generic string, `"Couldn't generate a draft — try again"`
(`architecture/06-error-handling.md`'s exact wording for this component),
regardless of which check failed or whether the failure was a check-failure
versus a generation timeout/error. No new response schema, no `checks_passed:
false` 200 response.

**Rationale**: `architecture/07-api-spec.md`'s `/api/drafts` route is already
specified this way — `'422': ... REQ-M10-07 pre-display checks failed — no
partial draft is ever returned` — and `ErrorResponse` is the same shape every
other route's failure path already uses. This directly implements
Clarifications' (2026-08-16) "same generic message, no specific reason,
no silent auto-retry beyond the one already defined for generation errors"
decision — the transport mechanism (422) was already decided by
architecture before this feature existed; this decision just confirms no new
mechanism needs inventing to satisfy it.

**Alternatives considered**: A `200` response carrying `checks_passed:
false` and a partial draft — rejected outright; `architecture/07-api-spec.md`
never describes this shape, and REQ-M10-07 itself requires a failed draft to
never reach display, which a `200` response inherently risks a frontend bug
exposing.

## Decision 8 — Talking points: no new column, no `is_call` flag

**Decision**: REQ-M10-06's "call, don't email — talking points" output is
represented as ordinary `draft_text` content — the generated text itself
states the medium explicitly ("Call Ana rather than emailing — here's what
to cover: ...") and lists the points, still populating the same NOT NULL
`tone_variant` column (e.g. `direct`) and the same non-empty
`evidence_event_ids` constraint. No new `is_call` boolean, no schema change.

**Rationale**: Neither `DraftRequest` nor `DraftResponse`
(`architecture/07-api-spec.md`) nor `draft_messages`
(`data-base/10-ddl-appendix.md`) has a field for this distinction — and
REQ-M10-06 only requires the system to "say so explicitly," which the
generated prose can do on its own, exactly the way `architecture/
06-error-handling.md`'s deterministic Narrator fallback headline is "clearly
marked as auto-generated" through its own wording, not a dedicated flag.
Avoids a real schema change (a genuine migration) for a distinction the
existing contract never asked for — consistent with P10 (YAGNI).

**Alternatives considered**: Adding `is_call: bool` to `DraftResponse` only
(API-level, no DB column) — rejected as an unnecessary indirection; the
frontend has no different rendering requirement for a call-suggestion draft
versus a written one (both render as read-only text the CS lead copies or
acts on), so a flag with no consumer isn't worth adding.

## Decision 9 — Tone variants are separate generation calls, not a stored array

**Decision**: Requesting "a different tone variant" (REQ-M10-05) issues a new
`POST /api/drafts` call with a different `tone_variant`, producing a new
`draft_messages` row — not an in-place update of an existing row, and not a
`variants[]` array on one row.

**Rationale**: `draft_messages.tone_variant` is a single, NOT NULL column per
row (`data-base/10-ddl-appendix.md`), and `DraftRequest` requires
`tone_variant` on every call — the schema was already built this way, one
row per generation. This is the schema's own existing shape, not a new
design choice this feature introduces. Consequence, surfaced by
`/speckit-analyze` finding I1: each variant is a genuinely independent
generation call over the same evidence, not a rephrasing of the first
variant's exact text — `spec.md` SC-006 was softened to match what this
independence actually guarantees (truthfulness per variant, not an
identical fact set across variants).

**Alternatives considered**: A `draft_variant_texts` JSONB column holding all
three tones from one generation call — rejected; would be a real schema
change the already-ratified DDL doesn't have, for a UX REQ-M10-05 doesn't
actually require (offering variants doesn't require generating all three
up front).

## Decision 10 — Frontend: real content for two scaffolds

**Decision**: `frontend/src/draft-composer/` (currently `.gitkeep` only)
gets its first real content: `draft-composer-panel.tsx` (opens beside the
evidence, tone-variant tabs, "Copy draft"/"Log as sent (manual)" — no edit
control per FR-009a), `api.ts` (typed `POST /api/drafts` +
`/copy`/`/log-as-sent` client), `types.ts`. `frontend/src/ask/components/
answer-renderer.tsx`'s existing `DraftHandoff` stub (currently static text:
*"Ready to draft a message about this issue — open the draft composer to
continue"*) gets a real trigger — a link/button passing `component_props.
issue_id`/`stakeholder_id` through to the new panel.

**Rationale**: `decisions/02-repo-and-tooling.md`'s frontend package map
already reserves `frontend/src/draft-composer/` for M10; the stub's own code
comment (`// The one non-inline-answer case (FR-012a) — surfaces the handoff
context rather than composing a message itself (feature 009's job)`)
explicitly names this feature as the one that finishes it.

**Alternatives considered**: A modal/dialog instead of a panel — rejected in
favor of matching the base spec's own screen description exactly ("Draft
composer | Message editing beside its evidence," `base/...md` §11.2 — read
during `/speckit-clarify` as "interacting with the message," not literal
editing, but still "beside its evidence," i.e., alongside the evidence trace
panel feature 006 already built, not a separate full-screen or modal
navigation).

## Decision 11 — No Alembic migration

**Decision**: No migration. `draft_messages` and the `tone_variant` enum
already exist — created by feature 001's initial straight-DDL-import
migration (`data-base/10-ddl-appendix.md` lines 500–517, already granted to
`app_role`). This feature is the first real writer, the same status
`narrator_outputs`/`ask_queries` had before feature 008.

**Rationale**: Confirmed by reading the actual DDL file, not assuming from
the prose schema doc alone — the same "read the real DDL, not just the prose
description" discipline `specs/008-.../research.md` Decision 6 used for
`declined_reason`'s enum type.

## Decision 12 — Testing

**Decision**: All five check functions (`verify_facts`/`verify_dates`/
`verify_no_invented_cause`/`verify_no_leak`/`verify_no_concession`) are pure
and unit-tested directly against known-good/known-bad `(draft_text,
context)` pairs — no DB, no LLM, mirroring `test_fact_check.py`'s own
precedent exactly. `GenerateDraftUseCase` gets `LLMPort` faked in its own
test. A real-DB test exercises `POST /api/drafts` → `/copy` →
`/log-as-sent` end to end against the actual worked-example fixture
(`draft-1` to Ana), including a scripted red-team case per check. "Draft
quality" itself (is the generated message good) stays out of CI scope —
`tests/strategy.md` already excludes it explicitly, deferring to the
production metric "≥ 40% of drafts sent after light editing" (spec §14.2) —
this exclusion covers the two remaining prompt-only guarantees (blame,
exactly-one-ask, Decision 6), not the five mechanically-checked properties.

**Rationale**: Matches every prior feature's fake-in-tests precedent and
`tests/strategy.md`'s already-documented exclusion — no new testing
philosophy needed for this feature.

## Decision 13 — Stakeholder existence check (`/speckit-analyze` finding U3, 2026-08-16)

**Decision**: `StakeholderReadPort` (feature 008,
`app.experience.application.ports`) gains one new method: `get(
stakeholder_id: UUID) -> StakeholderRecord | None`. `GenerateDraftUseCase`
calls it before generating; `None` raises the same `404` `IssueReadPort.
get_issue_evidence` already produces for an unresolvable `issue_id`.

**Rationale**: `/speckit-analyze` found that `contracts/drafts.md` and
`plan.md` both asserted a `404` for an unresolvable `stakeholder_id`, but no
port method existed to check it — only `list_stakeholders()` (a full-list
read) was available. Adding a single-ID lookup method is the smaller change
than filtering the full list in the use case, and matches
`IssueReadPort.get_issue_evidence`'s own single-ID-lookup shape exactly.

**Alternatives considered**: Filtering `list_stakeholders()` in
`GenerateDraftUseCase` itself — rejected; correct but wasteful (fetches
every stakeholder to check one ID) and pushes a query concern into the
application layer that a repository method already exists to own
elsewhere in this codebase (`IssueReadPort`, `FindingReadPort.get_finding`).

## Decision 14 — Mechanical transport-import scan (`/speckit-analyze` finding G2, 2026-08-16)

**Decision**: A new test, `backend/tests/experience/
test_no_external_transport.py`, statically scans the source of every file
this feature adds or extends (`draft_router.py`, the `use_cases.py`/
`services.py`/`sqlalchemy_repository.py` additions, `application/prompts/
draft_composer_v1.py`) for an import of any outbound-transport client —
`smtplib`, `httpx`, `requests`, an SMTP/CRM/chat SDK name — and fails if any
is found.

**Rationale**: SC-004 requires "a code-level architecture review" that no
task previously performed mechanically — `POST /api/drafts/{id}/log-as-sent`
returning `204` with no route existing at `/send` (already tested, Decision
7) proves no *route* transmits externally, but doesn't prove no *code path*
could. A static import scan is the same "prove it mechanically, not by
inspection" discipline `test_ask_agent_toolkit.py`'s read-only-tool-
enforcement test already established in feature 008, applied to this
feature's own structural no-send guarantee (constitution P4).

**Alternatives considered**: A one-time manual code review, documented in
`quickstart.md` — rejected; matches exactly the "manual review, not a
mechanical guarantee" gap `/speckit-analyze` flagged, so it would not
actually close the finding, only restate it. An AST-based check (walking
`ast.parse()`'s import nodes) instead of a source-text scan — considered
for lower false-positive risk (e.g., a string literal mentioning "httpx" in
a comment wouldn't trigger it); left as an implementation-time choice
between the two, both satisfy this decision's intent.

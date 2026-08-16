# Phase 1 Data Model: Draft Composer

No new tables, no migration. `draft_messages` and the `tone_variant` enum
(`data-base/10-ddl-appendix.md`) already exist since feature 001's
`0001_initial_schema.py` — already granted to `app_role`, already listed in
`idx_draft_messages_issue_id`. This feature is the first real *writer* of
`draft_messages`, the same status `narrator_outputs`/`ask_queries` had before
feature 008 (`research.md` Decision 11).

One additive change to an existing port record (`research.md` Decision 5):
`ClientProfileRecord` gains `communication_norms: str | None`, mirroring
feature 006's own `renewal_date` addition to the same record.

## `draft_messages` (existing table, first real writer)

No column changes. `data-base/08-schema-experience.md`'s existing shape is
exactly what this feature writes:

| Field | Set by |
|---|---|
| `issue_id` | The requested issue — any issue with cited evidence, not only the top-ranked one (Clarifications, 2026-08-16) |
| `stakeholder_id` | The intended recipient, from the request |
| `requested_by_user_id` | From the bearer token, never the request body (`architecture/07-api-spec.md`, matching every other "who did this" column) |
| `draft_text` | The fact-checked, date-checked, leak-checked message — or, for the call-not-email case, prose stating that explicitly plus talking points (REQ-M10-06, `research.md` Decision 8) |
| `tone_variant` | One of `direct`/`formal`/`brief`, from the request — always set, including on the call-not-email path |
| `evidence_event_ids` | Non-empty by constraint — the issue's own cited events plus any thread-history events the draft references |
| `checks_passed` | Always `true` for a persisted row — a `false` result never reaches persistence; it's an HTTP `422`, not a stored row (`research.md` Decision 7) |
| `logged_manually_at` | `NULL` until "Log as sent (manual)" is clicked |
| `copied_at` | `NULL` until "Copy draft" is clicked |

## New domain value objects — `app.experience.domain.entities`

Pure, no I/O — consumed/produced by the five new `app.experience.domain.
services` functions (`research.md` Decision 6, revised to five checks per
`/speckit-analyze` findings G1/U1, 2026-08-16). `VerifiedFactSet`/
`FactCheckResult` are **not** redefined here — imported from
`app.narrator.domain.entities` (`research.md` Decision 2).

| Type | Fields | Description |
|---|---|---|
| `IssueEvidenceRecord` | `issue_id, label, finding_types: tuple[str, ...], cited_event_ids: tuple[UUID, ...]` | The requested issue's own aggregated evidence — `IssueReadPort.get_issue_evidence`'s return shape |
| `AgreedAction` | `text, owner, due_date, finding_type` | One of the run's already-narrated actions, filtered to this issue's finding types (`research.md` Decision 4) — the source of every date `verify_dates` accepts |
| `VerifiedDateSet` | `dates: frozenset[str]` | Every date/day-name token legitimately present in the issue's `AgreedAction`s and thread history — built once, before generation |
| `DateCheckResult` | `passed: bool, unverified_dates: frozenset[str]` | One candidate draft's date-check outcome |
| `CauseCheckResult` | `passed: bool, unverified_causal_clauses: frozenset[str]` | One candidate draft's invented-cause-check outcome (`research.md` Decision 6, `/speckit-analyze` finding U1) — every causal clause's numbers/names must already be in the same `VerifiedFactSet` `verify_facts` uses |
| `LeakCheckResult` | `passed: bool, leaked_terms: frozenset[str]` | One candidate draft's internal-leak-check outcome (denylist + other-client-name check) |
| `ConcessionCheckResult` | `passed: bool, matched_terms: frozenset[str]` | One candidate draft's discount/commercial-concession-check outcome (`research.md` Decision 6, `/speckit-analyze` finding G1) — closed denylist match |
| `DraftCheckResult` | `passed: bool, fact_check: FactCheckResult, date_check: DateCheckResult, cause_check: CauseCheckResult, leak_check: LeakCheckResult, concession_check: ConcessionCheckResult` | The composed result of all five checks — `passed` is `True` only if all five are |
| `GeneratedDraft` | `draft_text, tone_variant, evidence_event_ids: tuple[UUID, ...], check_result: DraftCheckResult` | The use case's pre-persistence result |

`DraftCheckFailedError(Exception)` — `app.experience.application.use_cases`
(not a domain value object; an application-layer exception) — raised by
`GenerateDraftUseCase` when `DraftCheckResult.passed` is `False`; carries no
detail about which check failed (`research.md` Decision 7). Documented here
per `/speckit-analyze` finding I2 — the one new type this feature
introduced without a data-model.md entry in the original pass.

## New ports — `app.experience.application.ports`

Extends the existing file (feature 006/008 already established it) — no new
package.

| Port | Method(s) | Used by |
|---|---|---|
| `IssueReadPort` | `get_issue_evidence(issue_id: UUID) -> IssueEvidenceRecord \| None` | `GenerateDraftUseCase` — the issue + evidence input (REQ-M10-01) |
| `PlaybookReadPort` | `finding_type_for_playbook(playbook_id: UUID) -> str \| None` | `GenerateDraftUseCase`, filtering the run's narrated actions to this issue (`research.md` Decision 4) |
| `DraftMessageRepositoryPort` | `persist(draft: GeneratedDraft, *, issue_id, stakeholder_id, requested_by_user_id) -> UUID`; `get(draft_id: UUID) -> DraftMessageRecord \| None`; `stamp_copied(draft_id: UUID) -> None`; `stamp_logged_manually(draft_id: UUID) -> None` | The three routes (`contracts/drafts.md`) |

Extended (existing port, feature 008): `StakeholderReadPort` gains
`get(stakeholder_id: UUID) -> StakeholderRecord | None` — `404` if `None`,
matching `IssueReadPort.get_issue_evidence`'s own not-found handling
(`research.md` Decision 13, `/speckit-analyze` finding U3).

Reused, unchanged: `ClientProfileRepositoryPort.get_current()` (extended
record, `research.md` Decision 5), `NarratorReadPort.get_latest()` (feature
008), `LedgerQueryPort.timeline_for_stakeholder()` (feature 008), `LLMPort`
(`app.readers.application.ports`, `research.md` Decision 1).

```python
@dataclass(frozen=True)
class ClientProfileRecord:
    client_name: str
    renewal_date: date | None = None
    communication_norms: str | None = None
    """New in this feature (research.md Decision 5) — the account-wide
    free-text communication norms REQ-M10-04 personalizes drafts against."""
```

## New adapters — `app.experience.adapters`

| Adapter | Implements | Notes |
|---|---|---|
| `SqlAlchemyIssueReader` | `IssueReadPort` | `issues` ⋈ `finding_issue_map` ⋈ `findings WHERE status = 'validated'` (matches `SqlAlchemyFindingReader.get_finding`'s existing validated-only filter) |
| `SqlAlchemyPlaybookReader` | `PlaybookReadPort` | `SELECT applies_to_finding_type FROM playbook_actions WHERE id = :id` |
| `SqlAlchemyDraftMessageRepository` | `DraftMessageRepositoryPort` | Extends `sqlalchemy_repository.py` (existing file) |
| `application/use_cases.py` (`GenerateDraftUseCase`) | — | Calls `LLMPort.generate_structured` with `application/prompts/draft_composer_v1.py`'s template; no new adapter class |
| `adapters/draft_router.py` | — | Constructs `AnthropicLLMAdapter(settings.anthropic_api_key, settings.generation_model_id)`, matching `ask_router.py`'s existing composition-root pattern |

`ClientProfileRepositoryPort`'s existing `SqlAlchemyClientProfileRepository`
gets one additive column read (`communication_norms`) — no new adapter
class. `StakeholderReadPort`'s existing `SqlAlchemyStakeholderReader`
(feature 008) gets one additive method (`get`) — no new adapter class.

A new test, `backend/tests/experience/test_no_external_transport.py`,
statically scans every file this feature adds/extends for an
outbound-transport import (`research.md` Decision 14, `/speckit-analyze`
finding G2) — not an adapter, but recorded here since it's this feature's
one new *cross-cutting* test file, alongside the per-story test files
listed in `plan.md`'s Project Structure.

## API contract deltas

See `contracts/drafts.md` for the full request/response shapes —
`architecture/07-api-spec.md` already documents `DraftRequest`/
`DraftResponse`/the three routes in full; this feature implements against
that existing contract with **zero schema changes**, the first feature since
006 to add no new fields to any existing response shape.

## Frontend types — `frontend/src/draft-composer/types.ts` (new)

```typescript
export type ToneVariant = 'direct' | 'formal' | 'brief'

export interface DraftRequest {
  issue_id: string
  stakeholder_id: string
  tone_variant: ToneVariant
}

export interface DraftResponse {
  id: string
  draft_text: string
  tone_variant: ToneVariant
  evidence_event_ids: string[]
  checks_passed: boolean
}
```

No `is_call`/`talking_points` field (`research.md` Decision 8) — the
call-not-email case is ordinary `draft_text` content.

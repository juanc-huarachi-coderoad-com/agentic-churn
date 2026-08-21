# Contract: Draft composer

`architecture/07-api-spec.md` already defines all three routes and their
schemas (`DraftRequest`, `DraftResponse`, `ErrorResponse`) — not re-specified
from scratch here. This feature is the first to actually implement them,
against the existing contract, with **zero schema changes** — the first
feature since 006 to add no new field to any documented request/response
shape.

## `POST /api/drafts`

- **Auth**: bearer token required, same as every other route
  (`contracts/auth.md`, feature 002). `requested_by_user_id` is taken from
  the token, never the request body — matches every other "who did this"
  column's existing discipline.
- **Request** (superseded by the 2026-08-21 Amendment below —
  `score_contribution_id`, not `issue_id`, is the real field):

```json
{
  "score_contribution_id": "sc-1",
  "stakeholder_id": "stk-ana",
  "tone_variant": "direct"
}
```

`score_contribution_id` is any finding's own score contribution with cited
evidence — not restricted to the current top-ranked one (Clarifications,
2026-08-16, applied to the new anchor by the Amendment). Rejects with `404`
if `score_contribution_id`/`stakeholder_id` don't resolve —
`ScoreReadPort.get_contribution`/`FindingReadPort.get_finding` or
`StakeholderReadPort.get(stakeholder_id)` returns `None` (`research.md`
Decision 13, `/speckit-analyze` finding U3, 2026-08-16 — the stakeholder
half of this check was undesigned in the original plan).

### Response (200) — all five pre-display checks passed

```json
{
  "id": "draft-1",
  "draft_text": "Ana — we took 19 hours to respond to ticket #456; we promised 4. Engineering is on it today, and I'll call you before Thursday.",
  "tone_variant": "direct",
  "evidence_event_ids": ["evt-2"],
  "checks_passed": true
}
```

`checks_passed` is always `true` on a `200` — a failing result never reaches
this shape (`research.md` Decision 7). The five checks are: facts exist in
evidence, dates are human-supplied, causal claims name only evidenced
entities, no internal-only leak, no discount/commercial concession
(`research.md` Decision 6, revised 2026-08-16 per `/speckit-analyze`
findings G1/U1).

### Response (422) — any pre-display check failed

```json
{ "detail": "Couldn't generate a draft — try again" }
```

The exact same `detail` string `architecture/06-error-handling.md` already
defines for a generation timeout/error — no distinction between "the model
errored" and "the model produced something that failed validation," and
never a message naming which specific check failed (Clarifications,
2026-08-16, `research.md` Decision 7). No partial draft, no `checks_passed:
false` body — REQ-M10-07's "blocks display, does not silently strip content"
made structural, not just a frontend convention.

### Response (404) — issue or stakeholder not found

```json
{ "detail": "Not found" }
```

## `POST /api/drafts/{id}/copy`

- **Auth**: bearer token required.
- **Response**: `204`, no body. Stamps `copied_at`.

## `POST /api/drafts/{id}/log-as-sent`

- **Auth**: bearer token required.
- **Response**: `204`, no body. Stamps `logged_manually_at` — an internal
  flag in this table only, never a write to any external system, including
  the CRM (REQ-M10-08). **There is no `/send` route — not in this contract,
  not anywhere in this feature, not disabled, not feature-flagged
  (REQ-M10-P1).** Backed by a mechanical test, not just this doc's own
  absence of a route: `test_no_external_transport.py` scans every file this
  feature touches for an outbound-transport import (`research.md`
  Decision 14, `/speckit-analyze` finding G2, SC-004).

## Tone variants

Requesting a different tone (REQ-M10-05) is a second `POST /api/drafts` call
with a different `tone_variant` — a new `draft_messages` row, not an update
to the first one (`research.md` Decision 9). The frontend does not
pre-generate all three; it generates on demand as the CS lead switches tabs.

## No in-app editing

There is no `PATCH`/`PUT` route on `/api/drafts/{id}` and none is added by
this feature — the displayed text is exactly what passed the checks
(FR-009a, Clarifications, 2026-08-16).

## Frontend wiring: the Ask agent's `draft_handoff` → this contract

`frontend/src/ask/components/answer-renderer.tsx`'s existing `DraftHandoff`
component (feature 008, currently static text only) gets a real trigger that
opens `frontend/src/draft-composer/draft-composer-panel.tsx` with
`component_props.issue_id`/`stakeholder_id` (`research.md` Decision 10) —
no backend contract change, `AskComponentResponse`'s schema is unchanged.

## Amendment — 2026-08-21: anchored to `score_contribution_id`, not `issue_id`

**What changed.** `POST /api/drafts`'s request body field is now
`score_contribution_id`, not `issue_id`. `GenerateDraftUseCase` resolves
evidence via `ScoreReadPort.get_contribution` + `FindingReadPort.get_finding`
— the exact same read path `GetEvidenceTraceUseCase` already uses for the
evidence trace panel — instead of `IssueReadPort.get_issue_evidence`.
`draft_messages.issue_id` is now nullable (kept, unused going forward);
`draft_messages.score_contribution_id` is the new required column
(`migrations/versions/0007_draft_finding_anchor.py`).

**Why.** `issues`/`finding_issue_map` (`specs/004-score-engine`) were always
fixture-only data — the only writer in the whole codebase is
`backend/scripts/seed_score_fixture.py`'s hand-authored "Issue A" worked
example, never a use case, background job, or reader. `specs/004-score-
engine/data-model.md` explicitly deferred real finding-to-issue clustering
to "feature 005," which never actually built it (feature 005's own
clustering merges raw *events* into one `recurring_issue`-type finding — an
unrelated mechanism). The result: `score_contributions.issue_id` was `NULL`
for every real finding, in every real account, always — confirmed by live
testing against the `demo-wara` account through both its Stage 1 and Stage 2
fixtures (score 64.5 → 98.47), where the Ask agent's `write_to_stakeholder`
handoff (`contracts/ask.md`) never once produced a non-null `issue_id`, so
this feature's entry point never actually worked outside the one seeded
fixture `test_draft_routes_real_db.py` depended on.

**What did not change.** `issues`/`finding_issue_map` themselves are
untouched, still available for a future real clustering effort — this
amendment only stops the Draft Composer from depending on data that effort
never shipped. The five pre-display checks, the tone-variant behavior, and
the no-edit/no-send guarantees are all unchanged.

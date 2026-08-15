# Data Model: Dashboard Evidence Trace

No new tables — `architecture/07-api-spec.md` already defines every response
shape this feature returns (`DashboardResponse`, `EvidenceTraceResponse`,
`CoverageResponse`), not re-specified here. This document covers the value
objects `app.experience.domain` introduces to compute those shapes from
existing rows, plus a worked example against the real, already-scored Meridian
fixture — the same fixture features 003–005 built and verified against.

## Domain value objects (`app.experience.domain.entities`)

Small, frozen dataclasses — `app.experience.domain.services`'s pure functions
consume/produce these, no I/O:

- **`DashboardState`** — one of the seven values `research.md`'s state-
  precedence Decision defines (`no_profile`, `source_down`, `unresolved_person`,
  `catching_up`, `learning`, `healthy_quiet`, `normal`), plus whichever
  interpolated values its message needs (a source name, a minute count, a
  domain, a signal-type count) — never a bare string the frontend has to parse.
- **`PulseSeverity`** — `info` / `watch` / `at_risk`, derived per
  `research.md`'s finding-type mapping.
- **`EvidenceComparison`** — `baseline_label: str`, `current_label: str`,
  `what_changed: list[str]` — the per-finding-type dispatch's output shape.
- **`ArithmeticClause`** — `text: str` (one plain-language sentence per
  non-neutral `score_contributions` factor); a list of these joins into
  `EvidenceTraceResponse.arithmetic_explanation`.

## Ports this feature adds (`app.experience.application.ports`)

Reader-owned, per `research.md`'s Decision — no cross-module adapter import:

- **`ScoreReadPort`** — latest `score_runs` row; last-14-days one-per-day score
  history; a `score_contributions` row by ID, joined to its `finding_type`.
- **`FindingReadPort`** — a `findings` row by ID (for citation resolution) and
  its `cited_event_ids` resolved to real `events` rows (occurred_at,
  decrypted body where present, `structured_payload`).
- **`PulseEventPort`** — validated `score_contributions` within the 14-day
  window, joined to their findings' cited events.
- **`StakeholderReadPort`** — the current profile's stakeholder list, each
  one's most recent real ledger activity, and whether that's within the 4-week
  window (reusing `RelationshipReader`'s own constant, feature 005).
- **`CoveragePort`** — `sources` (status, `last_successful_sync_at`), the
  latest `coverage_reports` row, and a source-type → "signal type" grouping
  for the Learning state's "N of 6" (`requirements/08-health-dashboard.md`'s
  own six: Tickets, Email, Chat, Product usage, Surveys, Meetings).
- **`IdentityGapPort`** — `events.structured_payload->>'participant'` grouped
  by value where `stakeholder_id IS NULL`, with a count, for the
  Unresolved-person state.

**Extended, not new** (`/speckit-analyze` finding CV2): `ClientProfileRecord`/
`ClientProfileRepositoryPort` (feature 002) gains `renewal_date: date` —
`ClientHeader.days_to_renewal`'s only source, `research.md`'s Decision. Not a
seventh port; the existing one already reads the same `client_profile_
versions` row.

## Evidence dispatch table

Already specified in full in `research.md`'s "evidence trace panel re-derives
baseline/current per finding type" Decision — not restated here, including its
fallback case (`/speckit-analyze` finding CV1) for a `finding_type` outside the
five entries.

## Worked example — against the real, currently-scored Meridian fixture

Reproducing `base/...md` §11.4's own illustrative shape ("base 12, doubled
because Ana signs the renewal, reduced because the reader was 80%
confident"), using this deployment's own real `broken_response_promise`
contribution (ticket #456, `score_contributions` row from the `manual`-
triggered run reproducing `examples/01`'s worked example, feature 004):

| Field | Real value |
|---|---|
| `finding_type` | `broken_response_promise` |
| `base` | 20.000 |
| `criticality` | 1.500 (`tracking_api` is `critical`) |
| `influence` | 1.000 (reporter never resolved to a named stakeholder) |
| `confidence` | 1.000 |
| `magnitude` | 1.000 (overdue ratio saturated) |
| `recency` | 1.300 (still `open_overdue` — the ageing multiplier, REQ-M6-09) |
| `damping` | 1.000 |
| `rank_within_issue_factor` | 1.000 |
| `points_contributed` | **39.000** |
| Cited event | `ticket_state_change`, ticket #456, "Slow API response", `reopened`, `tracking_api` |
| `response_pairs` for that event | `business_hours_elapsed = 50.00`, `state = open_overdue`, threshold `= 4.00` |

**`EvidenceTraceResponse` this feature would render for it**:

- `finding_type`: `broken_response_promise`, `points`: 39.000
- `baseline_value`: "responds within 4 promised business hours"
- `current_value`: "50.0 business hours elapsed, still open"
- `what_changed`: `["response time exceeded the promised threshold", "the ticket has not yet resolved"]`
- `quoted_messages`: the ticket's own title, "Slow API response," timestamped
  2026-08-10 12:40 UTC (no client-authored prose body on a
  `ticket_state_change` event — `quoted_text` is the structured title, still
  real, still attributed, never fabricated)
- `arithmetic_explanation`: "Base 20 points for a broken response promise,
  increased 50% because tracking_api is critical, increased 30% because the
  ticket is still open and overdue — 39.0 points total." (four factors sat at
  neutral — `influence`, `confidence`, `damping`, `rank_within_issue_factor` —
  correctly omitted, per `research.md`'s "skip neutral factors" rule)

This is a live, reproducible read against this deployment's real database —
verified at `quickstart.md` validation time, not hand-computed only here (the
exact `business_hours_elapsed`/timestamps depend on when the fixture was last
ingested, the same caveat `specs/005-deterministic-findings/data-model.md`
already gave its own timing-sensitive worked values).

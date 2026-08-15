# Research: Dashboard Evidence Trace

## Decision: `app.experience` gets its own reader-owned ports, no cross-module adapter import

**Decision**: New ports in `app.experience.application.ports` (`ScoreReadPort`,
`FindingReadPort`, `PulseEventPort`, `StakeholderReadPort`, `CoveragePort`,
`IdentityGapPort`) read `score_runs`/`score_contributions`/`findings`/`events`/
`coverage_reports`/`stakeholders`/`identity_map` directly via their own
SQLAlchemy adapter, never by importing `app.scoring.adapters.sqlalchemy_
repository.SqlAlchemyScoreRunRepository` (which already reads `score_runs`) or
any of `app.readers`/`app.ingestion`'s adapters.

**Rationale**: Feature 004 established this exact pattern for `app.scoring`
reading `app.ingestion`/`app.context`-owned tables; feature 005 repeated it for
`app.readers` reading `app.ingestion`-owned `rollups`. The constitution's own P8
names the rule generally ("an entity that spans modules... is defined once, in
the module that owns its lifecycle, and imported by the others — never
redefined per module"), and `.importlinter`'s `global-dependency-rule` contract
enforces the module boundary mechanically. `app.experience` is a pure *reader*
of five other modules' owned entities — exactly the situation this pattern
exists for.

**Alternatives considered**: Importing `SqlAlchemyScoreRunRepository` directly
— rejected for the same reason feature 004/005 rejected the equivalent shortcut:
it would couple `app.experience`'s adapter layer to `app.scoring`'s internal
adapter implementation for a query-shape convenience, breaking independent
replaceability and the `.importlinter` contract's module list.

---

## Decision: `ClientHeader.days_to_renewal` extends feature 002's existing `ClientProfileRepositoryPort`, not a new port

**Decision** (`/speckit-analyze` finding CV2): `architecture/07-api-spec.md`'s
`ClientHeader` schema — already ratified, unchanged by this feature — has
`band` and `days_to_renewal` alongside `client_name`. `band` is `score_block.
band` echoed (already covered by `ScoreReadPort`, no new source needed).
`days_to_renewal` has no source among the six new ports (none of them read
`client_profile_versions`). Rather than add a seventh port for one date field
this feature's own `Note on scope`/Key Entities already names
`client_profile_versions` as an in-scope read source for, `ClientProfileRecord`
(feature 002, `app.experience.application.ports`) gets one new field:
`renewal_date: date`. `SqlAlchemyClientProfileRepository.get_current()`
(feature 002, `app.experience.adapters.sqlalchemy_repository`) adds
`renewal_date` to its existing `SELECT`. `GetDashboardUseCase` computes
`days_to_renewal = (renewal_date - today).days` at read time — not stored,
always current.

**Rationale**: `client_profile_versions.renewal_date` already exists
(`data-base/04-schema-context.md`, feature 003) and this feature already
reads that table's sibling `client_name` field via this exact port — extending
an existing, single-purpose port with one more field from the same row is
simpler than introducing a new port for it (P10/YAGNI), and keeps `client_
header` assembly in one place rather than splitting it across two reads of
the same table.

**Alternatives considered**: A new `ClientProfileReadPort` duplicating feature
002's port for one extra field — rejected as exactly the kind of redundant
abstraction P10 already argues against; the existing port has no reason not
to grow by one field it was always adjacent to.

---

## Decision: the "arithmetic in words" is deterministic template formatting, never a model call

**Decision**: `app.experience.domain.services` formats `score_contributions`'
already-computed columns (`base`, `influence`, `criticality`, `confidence`,
`magnitude`, `recency`, `damping`, `rank_within_issue_factor`,
`points_contributed`) into plain-language clauses with a small, pure function —
one clause per factor that meaningfully deviates from neutral (1.000), skipping
factors at their neutral value, matching `base/...md` §11.4's own worked
example ("base 12, doubled because Ana signs the renewal, reduced because the
reader was 80% confident" — three clauses, not eight).

**Rationale**: Every number this sentence cites already exists as a stored
column on `score_contributions` — no new computation, no model call. This is
the same "the model interprets, code calculates" split (constitution P2) every
other module in this system already follows; spec.md's own Note on scope
already excludes Narrator (the one component that *would* call an LLM to write
prose) from this feature, and confirmed neither `DashboardResponse` nor
`EvidenceTraceResponse` (`architecture/07-api-spec.md`) has a field that would
require one.

**Alternatives considered**: Deferring the "arithmetic in words" field until
Narrator exists (feature 008) — rejected because `EvidenceTraceResponse.
arithmetic_explanation` is explicitly part of this feature's own scope
(`architecture/07-api-spec.md`), and every value it needs is already real
today; there's no reason to leave REQ-M8-08's most important component half-
built when nothing blocks finishing it.

---

## Decision: 14-day windows, reusing existing constants where one already exists for the same purpose

**Decision**: Four different "how far back" questions, three already answered
by reuse rather than a new number:

1. **Pulse timeline / score trend** — 14 days (`/speckit-clarify` session
   2026-08-15, spec.md's own resolved Clarification).
2. **Stakeholder `status = quiet` threshold** — 4 weeks (28 days), reusing the
   Relationship reader's existing rolling window (feature 005,
   `RelationshipReader`'s `_WINDOW_DAYS = 28`) rather than inventing a new
   constant for the same underlying question ("has this person been active
   recently?").
3. **Usage reader's 8-week statistical baseline** — untouched, not reused here;
   deliberately a different window for a different purpose (a normalcy
   baseline, not a recency window), per spec.md's own Assumptions.
4. **Score trend granularity** — one point per day (the day's last
   `score_runs` row), not one point per run. `hourly_heartbeat` (feature 004)
   creates a run every hour even with zero new findings, so a naive 14-day
   window of raw runs would be up to 336 points — noisy, not a meaningful
   sparkline. One point per day keeps the trend readable (≤14 points) while
   staying a direct, unaggregated read (the day's actual last score, not a
   computed daily average — REQ-M8-P1 still holds).

**Rationale**: Reusing an existing window constant where the underlying
question is the same ("has this stakeholder been active recently?") avoids a
third arbitrary number answering a question this codebase already answered
once. Where the purpose genuinely differs (statistical baseline vs. recency
window), keeping them distinct was already `/speckit-clarify`'s own resolution
rationale.

**Alternatives considered**: A fixed count (last 20 pulse events / 10 score
runs) instead of a time window — rejected during `/speckit-clarify` (Option A
chosen over Option B). Downsampling the score trend to fewer than one-point-
per-day (e.g., weekly) — rejected as too coarse for a 14-day window to show
any real movement.

---

## Decision: the pulse timeline shows finding-cited events only, not every raw ledger event

**Decision**: `PulseEventPort` returns one entry per real, validated
`score_contribution` (joined through its `finding_id` to that finding's
`cited_event_ids`) within the 14-day window — never a direct, unfiltered scan
of `events`.

**Rationale**: REQ-M8-09/FR-011's own filter — "any metric that would not
change a decision" — already rules out surfacing every raw ledger row (e.g.
every individual `usage_measurement` reading); showing only events a real,
validated finding actually cited is the same filter REQ-M8-08's evidence trace
panel already applies one level deeper. This also matches spec.md's own
Acceptance Scenario 4 wording exactly ("real ledger events cited by
findings").

**Severity mapping** (`PulseEvent.severity`): `info` for `is_positive`
findings; `at_risk` for `broken_response_promise`/`contact_absence` (the two
finding types FR-012/REQ-M8-10 already name as red-color triggers — a broken
promise, a disengaged sponsor); `watch` for every other negative finding type
(`usage_deviation`, `relationship_change`, `recurring_issue` — drift signals,
amber per FR-012). No new severity taxonomy invented — this reuses FR-012's
own red/amber rule verbatim.

**Alternatives considered**: Showing all `events` regardless of citation,
with severity `info` by default — rejected as exactly the kind of noise
REQ-M8-09 exists to prevent (a warehouse reading nobody would act on,
alongside a real broken promise, undifferentiated).

---

## Decision: dashboard `state` extends feature 002's existing field, with a defined precedence

**Decision**: `state` (feature 002's own field, currently `learning`/
`no_profile`) extends to seven values, in this fixed precedence (highest first,
matching spec.md's Edge Cases and Assumptions):

| `state` | Precondition |
|---|---|
| `no_profile` | No current `client_profile_versions` row (feature 002, unchanged) |
| `source_down` | Any `sources.status = 'disconnected'` |
| `unresolved_person` | Any `events.structured_payload->>'participant'` value with `stakeholder_id IS NULL` appears on 3 or more events (all-time, no window — see below) |
| `catching_up` | Latest `coverage_reports` row has `sources_read < sources_expected`, no source fully `disconnected` (i.e. `degraded`, not `down`) |
| `learning` | Fewer than 6 of the 6 counted signal types (`requirements/08-health-dashboard.md`'s own list: Tickets, Email, Chat, Product usage, Surveys, Meetings) have ever had a `sources.status IN ('connected', 'degraded')` row |
| `healthy_quiet` | Latest `score_runs.band = 'healthy'` AND zero `score_contributions` for that run |
| `normal` | None of the above — the full component set renders, styled by `client_header.band` |

**Rationale**: `no_profile` and `learning` already exist from feature 002 (this
feature only makes `learning`'s "N of 6" real instead of hardcoded 0);
`source_down`/`catching_up` map directly onto `sources.status`'s own three-
value enum (`connected`/`degraded`/`disconnected`) — no new classification
invented, the schema already drew this exact line; `healthy_quiet` is FR-004's
own explicit "Nothing needs you today" trigger, distinct from a merely-quiet-
looking `normal` render (an account could be `healthy` band with a small
positive contribution bar showing — still `normal`, not `healthy_quiet`).

**Unresolved-person counting, precisely**: every ingestion normalizer
(`SimulatedCollector`'s `_normalize_gmail`/`_normalize_zendesk`/
`_normalize_warehouse`, `app/ingestion/adapters/simulated_collector.py`) already
writes the raw sender/reporter address into `structured_payload.participant` —
this survives onto the `events` row regardless of whether identity resolution
succeeded, so counting is a direct `GROUP BY structured_payload->>'participant'
HAVING count(*) >= 3` over `events WHERE stakeholder_id IS NULL`, no new
tracking needed. **Known limitation, not solved here**: a source's own generic
system address (e.g. Zendesk's `support-desk@...` reporter, already exercised
by `tests/unit/test_simulated_collector.py`'s unresolved-identity test) would
also accumulate a count and could trigger a false "unresolved person" — this
feature does not attempt to distinguish a generic system mailbox from a real
unidentified human (no existing signal marks one vs. the other); worth revisiting
if it proves noisy in practice, not blocking for this feature's real,
demonstrable value.

**Alternatives considered**: A time-windowed unresolved-person count (last N
days) instead of all-time — rejected for now as an unnecessary extra parameter
matching no existing requirement; all-time is simpler (P10) and the state
naturally clears once a human adds the identifier to the profile.

---

## Decision: evidence trace panel re-derives baseline/current per finding type from the same projection tables the reader originally read

**Decision**: `findings` stores only `magnitude`/`confidence`/`cited_event_ids`
— not the reader's original comparison inputs. `GetEvidenceTraceUseCase` re-
derives the baseline-vs-current comparison at read time via a small, closed
dispatch keyed by `finding_type` (five entries, matching feature 005's five
readers — Recurrence's `recurring_issue` is the sixth `finding_type` but shares
Commitment's approach of reading straight from `cited_event_ids`):

| `finding_type` | Baseline | Current | Source |
|---|---|---|---|
| `broken_response_promise` / `commitment_met` | "responds within the promised threshold" | actual elapsed business hours | `response_pairs` joined on the cited event |
| `usage_deviation` | the metric's own rolling-window mean | the latest reading | `rollups` for the same subject/metric |
| `contact_absence` | the commitment's expected cadence | days since last real contact | the cited `absence`-type event's own `structured_payload` |
| `relationship_change` | "active within the last 4 weeks" | date of last real activity | the cited event's `occurred_at` |
| `recurring_issue` | "a single reported issue" | count of clustered occurrences | the finding's own `cited_event_ids` count |

**Rationale**: These are exactly the same tables/columns each reader already
read to make its original decision (feature 005) — re-reading them at evidence-
display time is a direct, current-state read (REQ-M8-01), not a new
computation, and stays correct even if a projection has since been rebuilt by
a replay (the comparison reflects "what's true about this citation now," the
same honesty principle `rollups`/`response_pairs` themselves already embody as
rebuildable projections).

**Alternatives considered**: Storing the baseline/current pair on `findings`
itself at emission time — rejected as a schema change this feature doesn't
need (every value is already re-derivable) and one that would freeze a stale
comparison rather than reflect the projection's current, replay-correct state.

**Fallback for a `finding_type` outside this five-entry table (`/speckit-
analyze` finding CV1)**: this deployment's own real, `validated`
`score_contributions` already include finding types feature 007's not-yet-
built Tone/Intent/CSAT readers will eventually own (`escalation_language`,
`tone_deterioration`, `csat_deviation` — seeded by `scripts/
seed_score_fixture.py`, verified present in the running database). A
contribution bar for one of these is real and clickable (FR-007 doesn't
exempt it), so `GetEvidenceTraceUseCase` must not raise an unhandled-dispatch
error for it. **Decision**: any `finding_type` not in the five-entry table
gets `evaluate_generic_evidence()` — `baseline_label`/`current_label` both
render "a detailed comparison for this finding type isn't available until
its owning reader ships"; `what_changed` is empty. This is the only case
where `EvidenceComparison`'s fields are honestly *absent* rather than
computed — never a fabricated per-type detail for a type this feature
doesn't yet understand. `quoted_messages` and `arithmetic_explanation` are
unaffected by this fallback: neither depends on the five-entry dispatch —
citation resolution and arithmetic formatting are already generic over
`score_contributions`' own stored columns, so they render fully real
regardless of `finding_type` (P1 still holds in full for those two fields).

---

## Decision: the evidence trace panel is a client-side overlay, not a route change

**Decision**: Clicking a score/contribution bar/pulse event opens the evidence
trace panel as an overlay on the same `/dashboard` route (`frontend/src/
evidence/evidence-panel.tsx`), fetching `GET /api/evidence/{id}` on open via
TanStack Query — the dashboard underneath is not unmounted, no route/URL
change.

**Rationale**: `base/...md` §11.4 and REQ-M8-08 both describe this as "opens
from any number" — a drill-down, not a navigation. Keeping the dashboard
mounted underneath preserves scroll position and matches "one click to the
reason, one more to the source message" (§11.6) as a layered reveal, not a
page transition.

**Alternatives considered**: A dedicated `/evidence/:id` route — rejected as
unnecessary navigation complexity for a read-only detail view with no
independent deep-link requirement in spec.md.

---

## Decision: the system health screen is its own route, not folded into the main dashboard

**Decision**: `GET /api/coverage` backs a new, separate `/coverage` frontend
route (`frontend/src/coverage/coverage-page.tsx`), distinct from the dashboard's
own coverage *line* (a one-line summary already part of `DashboardResponse`).

**Rationale**: `base/...md` §11.2's own screen inventory lists "System health"
as a separate screen from "Health dashboard" — the coverage line answers "is
something wrong?" at a glance; the dedicated screen answers "which source,
since when, and what's quarantined?" for someone who needs to act on it.

**Alternatives considered**: An expandable section on the dashboard itself —
rejected as contrary to the base spec's own explicit screen inventory.

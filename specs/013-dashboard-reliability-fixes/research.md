# Phase 0 Research: Dashboard Reliability Fixes

No `NEEDS CLARIFICATION` markers remain — the spec was written after directly reading the three affected files, so the fix direction for each was already confirmed against real code before this phase started. What follows records the exact chosen approach and why, per file.

## Decision 1: Key `DeltaBreakdown`/`RankedIssues` rows by `score_contribution_id`

**Decision**: In `frontend/src/ask/components/answer-renderer.tsx`, change `key={cause.finding_type}` (in `DeltaBreakdown`) and `key={issue.finding_type}` (in `RankedIssues`) to `key={cause.score_contribution_id}` / `key={issue.score_contribution_id}`.

**Rationale**: Both functions already receive the same `Cause` interface, which already declares `score_contribution_id: string` — present on the wire today (`app.experience.adapters.ask_agent_graph.py's query_score_runs`, per the existing code comment) and typed on the frontend since feature 010. It uniquely identifies the underlying finding a row represents, unlike `finding_type`, which is a category that can legitimately repeat (two separate `broken_response_promise` findings are two different events, not the same row). No new field, no backend change — purely swapping which already-present field keys the list.

**Alternatives considered**:
- Composite key (`` `${finding_type}-${index}` ``) — rejected: array index as part of a key defeats the purpose of keying by identity (React's classic index-key anti-pattern) and provides no benefit over the genuinely unique field already available.
- A new backend-generated synthetic key — rejected: unnecessary; `score_contribution_id` already satisfies uniqueness, per P10/YAGNI.

## Decision 2: Scope the pulse-event e2e locator with `.first()`

**Decision**: In `frontend/e2e/dashboard-to-evidence.spec.ts`, change `page.getByText('"Slow API response"')` to `page.getByText('"Slow API response"').first()`.

**Rationale**: The same file's neighboring test (`clicking a contribution bar opens the evidence panel`) already uses this exact pattern (`page.getByRole('button', { name: /broken response promise/i }).first()`) for the identical problem — multiple real rows matching the same text. `.first()` keeps the test genuinely exercising a real click-through (a real DOM element is clicked, its real evidence panel opens, the same quoted text is confirmed in that panel) rather than weakening the assertion into something that could pass without a real click (FR-006). It also requires no seed-data changes and keeps working whether the shared dataset has one matching event or several.

**Alternatives considered**:
- Filter by a `data-testid` unique per event (e.g. `event_id`) — rejected: would require adding new test-only attributes to `pulse-timeline.tsx`, a larger and less proportionate change than an existing, already-used one-line pattern in the same file.
- Reset/reseed the database before this test to guarantee exactly one match — rejected: out of scope per the spec's Assumptions (no new seed/reset step), and would make the test slower and coupled to fixture maintenance instead of being robust to real data shape.

## Decision 3: Replace the "still learning" assertion with the feature-012 sidebar landmark

**Decision**: In `frontend/e2e/login-to-dashboard.spec.ts`, remove `await expect(page.getByText(/still learning/i)).toBeVisible()` and replace it with `await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible()`.

**Rationale**: The test's own name is "logging in with valid credentials reaches the dashboard shell" — its job is to prove a successful login reached a real, rendered dashboard, not to prove the account is in any specific state. The existing `getByRole('heading', { name: 'Meridian Logistics' })` assertion (kept, unchanged) already proves real account content rendered; adding the sidebar's `nav[aria-label="Primary"]` landmark (introduced by feature 012, present in every dashboard state except the two intentionally near-empty ones — `no_profile`/`healthy_quiet` — which this account is never expected to be in during normal seeded operation) strengthens the "reaches the dashboard *shell*" claim structurally, without depending on account state that drifts over hours of local development.

**Alternatives considered**:
- Simply delete the line with no replacement — rejected: the existing heading assertion alone is a valid minimal fix, but adding the shell landmark better matches what the test's name promises ("reaches the dashboard shell") and costs nothing extra.
- Assert on `data.state` via an API response intercept instead of DOM content — rejected: heavier test-infrastructure change (network interception) for a problem a one-line DOM assertion already solves; disproportionate per P10.

# Feature Specification: Dashboard Reliability Fixes

**Feature Branch**: `013-dashboard-reliability-fixes`

**Created**: 2026-08-17

**Status**: Draft

**Input**: User description: "Fix three reliability problems discovered while manually and automatedly testing the dashboard visual redesign (feature 012), all pre-existing and unrelated to that feature's own code: (1) frontend/src/ask/components/answer-renderer.tsx's DeltaBreakdown component uses `key={cause.finding_type}` when rendering the Ask agent's list of causes, but real backend data can legitimately contain multiple causes with the same finding_type (e.g. two separate 'broken_response_promise' findings), which produces a React "duplicate key" console warning and risks React silently dropping/misidentifying list items; the key must uniquely identify each cause even when finding_type repeats. (2) frontend/e2e/dashboard-to-evidence.spec.ts's test 'clicking a pulse event opens the evidence panel with the real quoted message' locates an event by `page.getByText('"Slow API response"')`, which now matches two separate pulse events in the long-running seeded dev database (their quoted_text happened to converge over time) and throws a Playwright strict-mode violation; the locator must reliably select a single specific event regardless of how many events share the same quoted text. (3) frontend/e2e/login-to-dashboard.spec.ts's test 'logging in with valid credentials reaches the dashboard shell' asserts `getByText(/still learning/i)` is visible after login, but the seeded 'marta'/Meridian Logistics account has since progressed out of the 'learning' dashboard state as the worker container accumulated more events over hours of local development, making the assertion state-dependent on wall-clock data drift rather than a fixed, reproducible fixture state. CRITICAL CONSTRAINT: these are narrowly-scoped correctness/reliability fixes only — no dashboard visual/layout changes, no changes to business logic, scoring, or any backend calculation; e2e fixes must make the tests robust against the natural growth of the shared long-running dev/demo dataset rather than pinning to today's exact data snapshot."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The Ask agent's answer never warns about or risks losing duplicate-finding-type rows (Priority: P1)

A Customer Success manager asks the AI assistant a question whose answer includes two or more causes or ranked issues that happen to be the same finding type (e.g. two separate "broken response promise" findings). Every row is rendered correctly and distinctly, with no risk of React silently dropping or misidentifying one of them because they looked identical to the rendering layer.

**Why this priority**: This is the one genuine application-correctness issue among the three — a React list-identity bug can, under the right conditions, cause rows to be dropped, merged, or to retain stale state across re-renders. It affects what a real user sees, not just test output, so it outranks the two test-only fixes.

**Independent Test**: Render the Ask agent's answer with a `causes` (or `ranked_issues`) array containing two entries with the same `finding_type` but different `score_contribution_id`s; confirm both rows render, each remains clickable to its own correct evidence, and no console warning about duplicate keys is produced.

**Acceptance Scenarios**:

1. **Given** an Ask agent answer whose causes include two entries with the same finding type but different underlying findings, **When** the answer renders, **Then** both rows appear as separate list items with their own correct point values.
2. **Given** the same duplicate-finding-type answer, **When** a CS manager clicks each row, **Then** each opens the evidence panel for its own specific finding, never the other one's.
3. **Given** the same duplicate-finding-type answer, **When** it renders, **Then** no "duplicate key" warning appears in the browser console.

---

### User Story 2 - The evidence-panel end-to-end test passes regardless of duplicate quoted text in the dataset (Priority: P2)

A developer runs the automated end-to-end test suite against the shared, long-running development database. The test verifying that clicking a Signal Stream entry opens its evidence panel passes reliably, even after the database has accumulated multiple entries that happen to quote the same words.

**Why this priority**: This blocks CI/local confidence in a real, already-existing user flow (evidence click-through) whenever the shared dataset drifts — but the flow itself already works correctly today (confirmed manually); only the test's ability to detect regressions is at risk.

**Independent Test**: Run the affected end-to-end test against a database state where two or more Signal Stream entries share identical quoted text; confirm the test still passes by exercising one specific, unambiguous entry.

**Acceptance Scenarios**:

1. **Given** two or more Signal Stream entries with identical quoted text in the seeded database, **When** the end-to-end test runs, **Then** it completes without a "multiple elements matched" failure.
2. **Given** the fixed test, **When** it runs, **Then** it still genuinely verifies that clicking a specific entry opens the evidence panel with that entry's real evidence — not a weakened assertion that could pass without exercising the click-through.

---

### User Story 3 - The login end-to-end test passes regardless of which valid dashboard state the seeded account is currently in (Priority: P3)

A developer runs the automated end-to-end test suite against the shared, long-running development database. The test verifying that a successful login reaches the dashboard passes reliably, even after the seeded demo account has naturally progressed out of the specific state ("still learning") the test originally assumed.

**Why this priority**: Lowest risk of the three — this assertion was always about state that changes on its own as the account "matures," so it's the most purely cosmetic of the fixes and doesn't reflect any behavior a real user would notice.

**Independent Test**: Log in against a seeded account that is currently in any valid, non-error dashboard state; confirm the test still passes by verifying the login reached the dashboard with real, honest content, without asserting a specific state that may have already passed.

**Acceptance Scenarios**:

1. **Given** the seeded demo account is in whatever dashboard state it has currently reached, **When** the login end-to-end test runs, **Then** it passes without depending on that account being in the "learning" state specifically.
2. **Given** the fixed test, **When** it runs, **Then** it still genuinely verifies a successful login reaches `/dashboard` and renders real account content — not a weakened assertion that could pass even on a broken dashboard.

---

### Edge Cases

- What happens if a future Ask agent answer contains a cause whose `score_contribution_id` is somehow missing or empty? The rendering must not crash; a reasonable fallback identity should still let the row render (even if deduplication guarantees weaken in that unlikely case).
- What happens if the shared dev database is reset to a fresh, minimal seed with only one Signal Stream entry (no duplicates) or an account already past every early state? Both fixed tests must still pass in that case too — the fixes must not accidentally require duplicates or a specific state to exist.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The Ask agent's rendered cause and ranked-issue lists MUST use a per-row identity that stays unique even when multiple rows share the same finding type, using the identifying information already present on each row.
- **FR-002**: Rendering an Ask agent answer containing multiple causes or ranked issues with the same finding type MUST NOT produce a browser console warning about non-unique list keys.
- **FR-003**: Each cause/ranked-issue row MUST continue to open the evidence panel for its own specific finding when clicked, even when another row shares the same finding type.
- **FR-004**: The end-to-end test that verifies clicking a Signal Stream entry opens its evidence panel MUST pass regardless of how many entries in the seeded database currently share identical quoted text.
- **FR-005**: The end-to-end test that verifies a successful login reaches the dashboard MUST pass regardless of which valid, non-error dashboard state the seeded account currently occupies.
- **FR-006**: Neither end-to-end fix MUST weaken what the test actually verifies — each must still exercise and confirm the real user-facing behavior it was written to protect (evidence click-through; successful login reaching real dashboard content), not merely be relaxed until it stops failing.
- **FR-007**: These fixes MUST NOT change any dashboard visual/layout behavior, business logic, scoring, or backend calculation — this is a correctness/reliability fix only, not a feature change.

### Key Entities

- **Cause / ranked issue row**: An item in the Ask agent's structured answer, already carrying a finding type, point value, and a unique underlying finding identifier — no new data is introduced; this feature only changes which existing field is used to identify each row for rendering purposes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero console key-uniqueness warnings are produced when the Ask agent renders an answer containing causes or ranked issues with duplicate finding types.
- **SC-002**: The evidence-panel end-to-end test passes on 10 consecutive runs against the shared dev database without a "multiple elements matched" failure.
- **SC-003**: The login end-to-end test passes on 10 consecutive runs against the shared dev database regardless of the seeded account's current dashboard state.
- **SC-004**: 100% of the automated test suites that were passing before this fix (unit, component, and the two other unaffected end-to-end tests) continue to pass after it.

## Assumptions

- The `score_contribution_id` field already present on each cause/ranked-issue row is unique per underlying finding and safe to use as the row's rendering identity — no new field or backend change is required.
- Fixing the two end-to-end tests means making their locators/assertions more specific or state-independent (e.g. scoping to a known-unique element, or asserting on state-independent successful-login evidence), not introducing new seed-data resets, new backend fixtures, or new test-only API endpoints.
- The shared, long-running development database is expected to keep growing and drifting during normal local development; these fixes must remain valid as that drift continues, not just at today's snapshot.
- No production/user-facing behavior beyond the Ask agent's rendering (User Story 1) is in scope — User Stories 2 and 3 are test-suite-only changes with no runtime user impact.

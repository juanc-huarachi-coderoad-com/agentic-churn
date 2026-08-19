# Quickstart: Validating the Dashboard Mockup V2 Refinement

This is a validation guide, not a setup guide — see the repo `README.md` and
`docker-compose.yml` for full environment setup. It assumes a running backend + database
(`docker compose up`) seeded with at least one account that has active findings, score
history, and Signal Stream events spanning more than one `event_type`.

## Prerequisites

- Backend + Postgres running (`docker compose up`), with a seeded account that has: active
  findings (non-`healthy_quiet` state), at least 2 score-history points, at least one
  `contribution_bars` entry, and pulse events covering at least two distinct
  `event_type` values (e.g. one `ticket_state_change`, one `usage_measurement`) at two
  different severities — needed to see the dual-channel icon (FR-005a) actually vary.
- A second seeded account (or the same account toggled) in the `healthy_quiet` state, to
  validate FR-017.
- Frontend dependencies installed and up to date after this feature's
  `@radix-ui/react-dialog` addition:

```bash
cd frontend
pnpm install
```

## Run the app

```bash
pnpm dev
```

Log in and navigate to `/dashboard`.

## Validate User Story 1 — three-column, full-height layout (P1)

1. Open `/dashboard` for the account with active findings.
2. **Expect**: three columns visible side by side, each filling the viewport height
   (FR-001, FR-002).
3. Add enough Signal Stream entries (or resize the window) that column 2's content
   exceeds its height; scroll inside it. **Expect**: only column 2 moves — columns 1 and 3,
   and the page itself, stay fixed (SC-004).
4. Narrow the browser window below the app's existing responsive breakpoint. **Expect**:
   the layout reflows consistent with how Coverage/Profile already handle narrow viewports,
   not clipped content (FR-018).

## Validate User Story 2 — enhanced Churn Risk Overview (P2)

1. On the same account, confirm column 3 shows the score at large, prominent size, colored
   by its current band (FR-009).
2. Confirm the trend chart shows visible `%`-labeled Y-axis ticks and sequence-labeled
   X-axis ticks without hovering (FR-010).
3. Compare every displayed number (score, trend values, driver labels/points) against the
   raw `GET /api/dashboard` JSON for that account — values must match exactly (SC-002).
4. Load an account with fewer than 2 score-history points; confirm the chart still degrades
   gracefully (single labeled point / "not enough history yet"), same as before this
   feature.

## Validate User Story 3 — Signal Stream by real type and severity (P3)

1. Confirm each Signal Stream entry shows elapsed time, a type label + icon shape matching
   its real `event_type`, a severity-colored ring (not a sentiment label), and a connecting
   timeline line between entries (FR-005, FR-005a, FR-007, FR-008).
2. Cross-check two entries with different `event_type` values against the raw
   `GET /api/dashboard` response — each entry's icon shape and label must match its own
   `pulse_timeline[].event_type`, never a generic or fabricated one (SC-006).
3. Confirm `NarratorPanel`, `StakeholderCards`, and `CoverageLine` still render, now
   appended below the Signal Stream entries within the same scrollable column 2 (FR-019).

## Validate User Story 4 — docked AURA Assistant (P4)

1. Reload `/dashboard`; confirm the Assistant is already expanded and ready to accept a
   message directly below the AURA risk orb in column 1 — no click needed to open it
   (FR-004, SC-007).
2. Scroll within column 2 or column 3; confirm the Assistant panel in column 1 stays
   visible and unaffected.
3. Ask a question; confirm the existing `idle → thinking → answered` behavior is unchanged
   (same `postAsk` call, same `AnswerRenderer`).
4. Confirm columns 2 and 3 are never obscured or resized by the docked Assistant panel.

## Validate User Story 5 — elegant modal + selectable affordance (P5)

1. Hover over a Signal Stream entry and an Action & Draft Hub item; confirm each shows a
   smooth visual affordance on its icon/body (FR-012).
2. Select a Signal Stream entry; confirm its details open in a centered modal (not a
   right-docked panel), containing the same information `EvidencePanel` shows today
   (FR-013).
3. With that modal open, trigger the Ask agent's "open draft composer" action; confirm the
   Evidence modal closes and the Draft Composer modal opens in its place — never both at
   once (FR-014, research.md Decision 3).
4. Press Esc, or click the backdrop; confirm the modal closes and the underlying columns'
   scroll position is unchanged (Edge Case).

## Regression check — FR-015 / FR-016

Run the existing automated suites; all should pass after being updated for new markup and
the one additive backend field (not new business behavior):

```bash
# Frontend
pnpm test          # vitest — component/unit tests
pnpm test:e2e       # playwright — end-to-end
pnpm typecheck
pnpm lint

# Backend
pytest backend/tests/unit/test_dashboard_route.py
```

Specifically confirm:
- `frontend/src/dashboard/dashboard-page.test.tsx` — still asserts the same `useQuery` call
  and the same conditional rendering by `data.state`; new assertion for mutually-exclusive
  modal state (Decision 3).
- `frontend/src/dashboard/pulse-timeline.test.tsx` — asserts icon shape varies by
  `event_type` and ring color varies by `severity` independently.
- `frontend/src/ask/ask-bar.test.tsx` — still asserts the same `useMutation`/`postAsk` call
  and idle/thinking/answered states; launcher/collapse assertions removed, replaced with
  "always rendered expanded" assertions.
- `frontend/src/evidence/evidence-panel.test.tsx`,
  `frontend/src/draft-composer/draft-composer-panel.test.tsx` — still assert the same props
  and data-driven content, now inside `Dialog`/`DialogContent`.
- `backend/tests/unit/test_dashboard_route.py` — `event["event_type"]` present and within
  the 7-value enum, alongside the existing `event["severity"]` assertion.

## Definition of Done for this feature

- All acceptance scenarios above pass manually.
- `pnpm test`, `pnpm test:e2e`, `pnpm typecheck`, `pnpm lint`, and
  `pytest backend/tests/unit/test_dashboard_route.py` all pass.
- A side-by-side screenshot comparison against `base/mockup-mainPage-v2.jpg` shows the
  three columns in their specified positions.
- `git diff --stat` shows no change to score computation
  (`backend/app/scoring/`), band classification, risk-driver ranking, draft generation, or
  any field on `DashboardResponse` other than the additive `pulse_timeline[].event_type`
  (FR-015).

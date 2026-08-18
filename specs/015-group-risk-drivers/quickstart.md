# Quickstart: Validating Grouped Risk Drivers

## Prerequisites

- `frontend/` dependencies installed (`pnpm install`).
- No backend/Docker Compose required — this feature is frontend-presentation-only; the
  new unit and component tests use in-memory fixture data, not a live API.

## Validate User Story 1 — duplicate labels collapse into one row (P1)

```bash
cd frontend
pnpm test src/dashboard/group-contribution-bars.test.ts src/dashboard/contribution-bars.test.tsx
```

Expect: `group-contribution-bars.test.ts` confirms same-label bars sum into one group
with the correct net points and full `contribution_ids` list, a single-label bar passes
through as a group of one, and groups sort by `|points|` descending.
`contribution-bars.test.tsx` confirms the rendered list shows one row per distinct
label, a `×N` badge only when `N > 1`, and that a single-signal row still calls
`onSelect` directly with no extra click (matching today's behavior, FR-004).

## Validate User Story 2 — every individual signal stays traceable (P1)

Covered by the same `contribution-bars.test.tsx` run above: expanding a grouped row
reveals one sub-row per contributing signal, and clicking a specific sub-row calls
`onSelect` with that signal's own `score_contribution_id` — never another signal's id,
and never a call with multiple ids.

## Manual visual check

```bash
pnpm dev
```

Open a client dashboard whose latest score run has several findings sharing a label
(any client with a "Churn Risk Overview" card showing repeated driver names before this
change — e.g. the seeded demo data mentioned in this repo's git history). Confirm:

1. Each distinct driver label appears once in "Top Risk Drivers."
2. A label with more than one contributing finding shows a `×N` badge next to it.
3. Clicking that row expands it to show each original finding; clicking one opens the
   `EvidencePanel` for that specific finding (verify the quoted evidence text matches
   the finding you clicked, not a different one).
4. A label with only one finding opens its evidence directly on click, same as before
   this change.
5. Rows are ordered by combined impact, highest first.

## Regression check

```bash
pnpm typecheck
pnpm lint
pnpm test
```

All must pass. Expect changes confined to `frontend/src/dashboard/group-contribution-bars.ts`
(new), `frontend/src/dashboard/group-contribution-bars.test.ts` (new),
`frontend/src/dashboard/contribution-bars.tsx` (modified), and
`frontend/src/dashboard/contribution-bars.test.tsx` (new) — no backend, no `types.ts`,
no `evidence/`, no `dashboard-page.tsx`, no `action-draft-hub.tsx` diff (verifiable with
`git diff --stat`, matching FR-008/FR-009).

## Definition of Done

- Both acceptance-scenario sets above pass (User Story 1 and User Story 2).
- `pnpm typecheck`, `pnpm lint`, `pnpm test` all pass.
- Manual visual check confirms grouped rows, count badges, expand/collapse, and correct
  per-finding evidence linking on the real running dashboard.
- No diff outside the four files listed above.

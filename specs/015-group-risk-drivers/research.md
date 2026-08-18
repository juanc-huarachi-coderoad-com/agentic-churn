# Phase 0 Research: Group Repeated Risk Drivers

Technical Context left no `NEEDS CLARIFICATION` markers — this feature reuses the
existing frontend stack end to end. This document records the decisions made while
resolving the "how" (already implemented), in the standard Decision/Rationale/
Alternatives format.

## Decision 1: Group client-side only, not in the API

**Decision**: Grouping happens entirely inside the frontend render layer (a new pure
function consumed by `ContributionBars`). `contribution_bars` in the API response stays
exactly 1:1 with `score_contributions` rows.

**Rationale**: `specs/006-dashboard-evidence-trace/quickstart.md` tests this 1:1 shape
explicitly ("the row count matches `contribution_bars`'s length exactly — no extra, no
missing"). Changing the API shape would require updating that contract, its test, and
every other consumer of `contribution_bars` (`dashboard-page.tsx`'s `topContributionId`
selection, `action-draft-hub.tsx`'s own ranking) — none of which have this duplication
problem, since they don't render the label as user-facing text the way
`ContributionBars` does. Confining the change to the one component with the actual
problem is the smaller, safer change (P10).

**Alternatives considered**:
- *Aggregate in the backend use case* (`use_cases.py`'s `contribution_bars` construction):
  rejected — breaks the tested 1:1 evidence-trace contract and would need a new field
  shape (e.g. a list of ids per bar) that every other consumer of `ContributionBar`
  would have to learn to handle, for a problem that is purely about how one list is
  displayed.
- *Add a `GROUP BY` to `list_contributions`'s SQL query*: rejected for the same reason,
  plus it would silently lose the acceptance criteria in feature 006 (each row traces to
  one real `score_contributions` id) at the data layer, not just the view.

## Decision 2: Sum net signed points, not raw magnitude

**Decision**: A grouped row's `points` is the sum of each contributing bar's already-
displayed signed value (`is_positive ? -Math.abs(points) : Math.abs(points)`), and the
group's own `is_positive` is derived from the sign of that sum.

**Rationale**: This is the same number a user would get by mentally adding up the
individual rows shown today — no new arithmetic convention introduced, so the displayed
total is self-evidently consistent with the (still available, via expand) individual
rows.

**Alternatives considered**:
- *Sum raw magnitude, ignore sign*: rejected — would misrepresent a group containing
  both risk-increasing and risk-reducing signals of the same label as more severe than
  its true net effect.
- *Show the single largest-magnitude signal only, hide the rest from the total*:
  rejected — silently discards real point contributions from the headline number, which
  the spec's Assumptions section rules out ("net combined effect... is a simple sum").

## Decision 3: Local `useState` for expand/collapse, no new state library

**Decision**: Which group (if any) is expanded is tracked with one `useState<string |
null>` local to `ContributionBars`.

**Rationale**: This is transient, component-local UI state with no cross-component or
cross-page consumer — exactly the case P11 reserves for local `useState` rather than
Zustand ("global client state... used sparingly... state lives as close to its owner as
possible"). No existing accordion/expand primitive exists in this codebase to reuse
(closest precedent: `AskBar`'s own local boolean `isOpen`, the same pattern).

**Alternatives considered**:
- *Zustand store for expanded state*: rejected — no other component needs to know or
  control which driver row is expanded; a global store would be pure overhead (P10).
- *Always show every individual signal, no collapsing*: rejected — reintroduces the
  exact visual-noise problem this feature exists to fix (User Story 1).

## Decision 4: No new count-badge or accordion component

**Decision**: The count indicator reuses the existing pill/badge styling already present
in `action-draft-hub.tsx` (`rounded-full px-2 py-0.5 text-xs font-medium`), and the
expand/collapse row is a plain `<button>` toggling a conditionally-rendered `<ul>` — no
new shared UI primitive is extracted.

**Rationale**: One consumer today (P10 — don't build a reusable abstraction for a single
call site); styling stays visually consistent with the rest of the dashboard without a
new dependency or design-system addition (P11's closed icon/component-library rule).

**Alternatives considered**:
- *Extract a shared `<Badge>` / `<Accordion>` component now*: rejected as premature —
  revisit if/when a second consumer needs the same pattern.

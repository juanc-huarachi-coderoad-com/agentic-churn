# Phase 1 Data Model: Group Repeated Risk Drivers

This feature introduces **no new domain entities and no changes to any existing
entity**. `frontend/src/dashboard/types.ts`'s `ContributionBar` and `DashboardResponse`
are unmodified and remain the source of truth (same guarantee feature 012 made for its
own view-model mapping). What follows is the one new derived, presentation-only view
model this feature adds.

## Source of truth: `ContributionBar[]` (unchanged)

```ts
// frontend/src/dashboard/types.ts — verbatim, not modified by this feature
export interface ContributionBar {
  score_contribution_id: string
  label: string
  points: number
  is_positive: boolean
}
```

One entry per real `score_contributions` row for the client's latest score run
(feature 006's contract) — still true after this feature; nothing here changes what
`DashboardResponse.contribution_bars` contains or how many entries it has.

## Derived, presentation-only value: `GroupedContributionBar`

Exists only inside `frontend/src/dashboard/group-contribution-bars.ts` and the render
layer that consumes it. Recomputed on every render from `bars` already passed down;
nothing is fetched, stored, or persisted — same category as feature 012's
`PriorityTier`.

```ts
export interface GroupedContributionBar {
  label: string
  points: number             // net sum of contributing bars' signed points
  is_positive: boolean       // derived: points <= 0
  contribution_ids: string[] // every score_contribution_id in this group, original order
}
```

**Construction rule**: group `ContributionBar[]` by `label`; for each group, `points` =
Σ `signedPoints(bar)` where `signedPoints(bar) = bar.is_positive ? -Math.abs(bar.points)
: Math.abs(bar.points)` (the same formula the UI already used per-row); `is_positive =
points <= 0`; `contribution_ids` collects every `score_contribution_id` in the group, in
encounter order. Output is sorted by `Math.abs(points)` descending.

**Cardinality**: `contribution_ids.length === 1` for a label that appears once (the
common case) — that row renders identically to today, no behavior change. `> 1` triggers
the count badge and expand affordance (FR-002, FR-005).

## Region mapping (extends feature 012's table)

| UI element | Sourced from | Notes |
|---|---|---|
| "Top risk drivers" row | `GroupedContributionBar` (derived from `contribution_bars`) | Replaces the previous direct 1:1 `ContributionBar` render; sorted by `\|points\|` descending (FR-007) |
| Count badge (`×N`) | `group.contribution_ids.length` | Shown only when `> 1` (FR-002, FR-004) |
| Expanded sub-row | The original `ContributionBar` looked up by each id in `group.contribution_ids` | Each still wired to the existing `onSelect(score_contribution_id)` callback, unchanged (FR-006) |

## State transitions

None. `expandedLabel` (`string | null`, local `useState` in `ContributionBars`) toggles
between at most one expanded group and none — a simple two-state UI toggle, not a
modeled entity lifecycle.

## Validation rules

None new. `points`/`is_positive`/`label` continue to come from server-validated,
already-typed data; this feature performs no new input validation because it accepts no
new input.

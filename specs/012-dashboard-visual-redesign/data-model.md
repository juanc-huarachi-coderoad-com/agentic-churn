# Phase 1 Data Model: Main Dashboard Visual Redesign

This feature introduces **no new domain entities and no changes to any existing entity**. `frontend/src/dashboard/types.ts`, `ask/types.ts`, `draft-composer/types.ts`, and `evidence/types.ts` are read-only for this feature (FR-011). What follows is the view-model mapping — how the untouched `DashboardResponse` shape is projected onto the four new visual regions — plus the two purely-presentational derived values introduced along the way (neither is persisted, fetched, or stored; both are computed at render time from props already present).

## Source of truth: `DashboardResponse` (unchanged)

```ts
// frontend/src/dashboard/types.ts — verbatim, not modified by this feature
interface DashboardResponse {
  client_header: ClientHeader | null
  state: DashboardStateKind
  message: string | null
  score_block: ScoreBlock | null
  contribution_bars: ContributionBar[]
  pulse_timeline: PulseEvent[]
  stakeholder_cards: StakeholderCard[]
  coverage_line: CoverageLine | null
  narrator: NarratorSummary | null
}
```

## Region mapping

| Mockup region | Sourced from (unchanged fields) | Notes |
|---|---|---|
| Navigation sidebar | N/A — static routes (`/dashboard`, `/coverage`, `/profile`) via `react-router` | No data dependency; active state from the router's current location, not `DashboardResponse` |
| Signal Stream | `pulse_timeline: PulseEvent[]` | `PulseEvent.occurred_at` → relative time, `severity` → icon/color, `quoted_text` → evidence-backed excerpt, `score_contribution_id` → still opens `EvidencePanel`, unchanged |
| Churn Risk Overview | `score_block: ScoreBlock` (`score`, `band`, `trend: number[]`) + `contribution_bars: ContributionBar[]` | `trend` becomes the Recharts `AreaChart` series (index-based x-axis, same array, same values — no timestamps existed before and none are added); `contribution_bars` becomes the ranked "Top risk drivers" rows, sorted by `Math.abs(points)` (already the sort key `dashboard-page.tsx` uses for `topContributionId`) |
| Action & Draft Hub | `contribution_bars: ContributionBar[]` only (research.md Decision 3/4/8 — `narrator.actions` has no ID and is not pulled in here) | Selecting an item opens `EvidencePanel` via the existing `score_contribution_id` → `onSelect` wiring, same as `ContributionBars`/`PulseTimeline` already do; `DraftComposerPanel` stays reachable only via the Ask agent's existing `onOpenDraftComposer` handoff, unchanged |
| Floating assistant | `ask/api.ts`'s existing `postAsk` mutation, unchanged | Only the wrapping shell (collapsed/expanded) is new local UI state — not conversation data |

## Derived, presentation-only values (not new data)

These exist only inside the render layer. They are recomputed on every render from props already passed down; nothing is fetched, stored, or persisted.

### `PriorityTier` (Action & Draft Hub badge)

```ts
type PriorityTier = 'high' | 'medium' | 'low'

// Pure function, frontend/src/dashboard/ — computed from the same `points`
// magnitude dashboard-page.tsx already uses to pick topContributionId.
function priorityTierFromPoints(absPoints: number): PriorityTier {
  if (absPoints >= 20) return 'high'
  if (absPoints >= 10) return 'medium'
  return 'low'
}
```

Thresholds are illustrative defaults for `/speckit-tasks` to carry into implementation; they are a display-only convenience (research.md Decision 3), not a scoring rule — changing them never changes `score_block.score` or any persisted value, only which badge color a row gets.

### Active nav route (sidebar highlight)

Derived from `react-router`'s `useLocation()` / `NavLink`'s built-in `isActive`, compared against the three static destinations — no component state, no new field on any entity.

## State transitions

None. No entity in this feature has a lifecycle beyond what `DashboardResponse.state` (`DashboardStateKind`) already governs today, and that state machine is untouched:

`no_profile | source_down | unresolved_person | catching_up | learning | healthy_quiet | normal`

The redesigned layout renders conditionally on this existing value exactly as `dashboard-page.tsx` does today (FR-010) — only the `normal`-state markup changes shape.

## Validation rules

None new. All validation (score bounds, band enum, event shape) happens server-side today and is unchanged; the frontend continues to trust the shape TypeScript already declares.

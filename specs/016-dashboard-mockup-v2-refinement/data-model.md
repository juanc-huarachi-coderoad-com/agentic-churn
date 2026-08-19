# Phase 1 Data Model: Dashboard Mockup V2 Refinement

This feature adds exactly **one field** to one existing entity (`PulseEvent.event_type`,
threaded through its backend chain) and introduces **no new persisted or fetched entity**.
Everything else below is either a view-model mapping of already-fetched data or a
presentation-only derived value computed at render time — nothing new is stored, and
`ask/types.ts`, `draft-composer/types.ts`, and `evidence/types.ts` are untouched.

## Changed entity: `PulseEvent` gains `event_type`

```ts
// frontend/src/dashboard/types.ts
export type SignalType =
  | 'message'
  | 'ticket_state_change'
  | 'usage_measurement'
  | 'survey_response'
  | 'meeting'
  | 'absence'
  | 'crm_change'

export interface PulseEvent {
  event_id: string
  occurred_at: string
  event_type: SignalType   // NEW — raw, unfiltered from events.event_type
  severity: 'info' | 'watch' | 'at_risk'
  quoted_text: string | null
  score_contribution_id: string
}
```

Backend chain (each layer gains the same field, no layer skipped — P8):

| Layer | File | Change |
|---|---|---|
| Adapter (query) | `sqlalchemy_repository.py`, `SqlAlchemyPulseEventReader.list_recent` | Inner `SELECT` adds `e.event_type`; outer `SELECT` list adds `event_type` |
| Application (port) | `ports.py`, `PulseEventRecord` | Adds `event_type: str` |
| Application (use case) | `use_cases.py`, `PulseEventResult` + `execute()` | Adds `event_type: str`; mapping passes `p.event_type` through verbatim |
| Adapter (HTTP schema) | `dashboard_router.py`, `PulseEvent(BaseModel)` | Adds `event_type: str` |
| Docs | `architecture/07-api-spec.md` | `PulseEvent` OpenAPI schema gains `event_type: { type: string, enum: [...] }` |

No new column, no migration — `events.event_type` (`data-base/10-ddl-appendix.md` lines
124-127) already exists and is simply selected for the first time by this reader.

## Presentation-only derived values (not new data)

### `signal-type.ts` — closed type→display map

```ts
// frontend/src/dashboard/signal-type.ts
import type { LucideIcon } from 'lucide-react'
import type { SignalType } from './types'

export const TYPE_LABEL: Record<SignalType, string> = {
  message: 'Message',
  ticket_state_change: 'Ticket',
  usage_measurement: 'Activity',
  survey_response: 'Survey',
  meeting: 'Meeting',
  absence: 'Absence',
  crm_change: 'CRM Update',
}

export const TYPE_ICON: Record<SignalType, LucideIcon> = {
  message: Mail,
  ticket_state_change: Ticket,
  usage_measurement: BarChart3,
  survey_response: ClipboardList,
  meeting: Calendar,
  absence: UserX,
  crm_change: Building2,
}
```

Fixed, closed, 7-entry table — one row per real `SignalType` value, no fallback branch
needed for an "unknown" 8th value since the union type makes that unrepresentable at
compile time (P10: no speculative extensibility for a category the product doesn't have).
`pulse-timeline.tsx`'s existing `SEVERITY_ICON`/`SEVERITY_RING_CLASS` maps are unchanged in
shape; the entry icon now composes both: `TYPE_ICON[event.event_type]` picks the glyph,
`SEVERITY_RING_CLASS[event.severity]` picks the ring/color (FR-005a).

### `BAND_CHART_COLOR` — shared between `score-block.tsx` and the new orb

```ts
// Extracted from score-block.tsx (unchanged values) so aura-risk-orb.tsx
// imports the same constant instead of redeclaring the palette.
export const BAND_CHART_COLOR: Record<Band, string> = {
  healthy: '#a3a3a3',
  watch: '#f59e0b',
  at_risk: '#ef4444',
}
```

### Modal state (`dashboard-page.tsx`, component-local, not persisted)

```ts
// Existing state, now made mutually exclusive (research.md Decision 3):
const [selectedContributionId, setSelectedContributionId] = useState<string | null>(null)
const [draftHandoff, setDraftHandoff] = useState<{ issueId: string; stakeholderId: string } | null>(null)

// Opening one clears the other so at most one Dialog is ever open:
function openEvidence(id: string) {
  setDraftHandoff(null)
  setSelectedContributionId(id)
}
function openDraftComposer(issueId: string, stakeholderId: string) {
  setSelectedContributionId(null)
  setDraftHandoff({ issueId, stakeholderId })
}
```

## Region mapping (three-column layout)

| Mockup region | Sourced from (unchanged fields unless noted) | Notes |
|---|---|---|
| Column 1 — Company/AURA/Assistant | `client_header.client_name`, `client_header.days_to_renewal`, `score_block.score`/`band` | Title and renewal text move here from the old top header row (Decision 5); orb reuses `BAND_CHART_COLOR` (Decision 6) |
| Column 1 — Assistant | `ask/api.ts`'s existing `postAsk` mutation, unchanged | Only the wrapping shell changes (always expanded, docked in-flow instead of `fixed`); no new conversation state |
| Column 2 — Signal Stream | `pulse_timeline: PulseEvent[]`, now including `event_type` | Icon shape from `TYPE_ICON[event_type]`, ring/color from `SEVERITY_RING_CLASS[severity]` (FR-005a); connecting line is pure CSS between list items, no data dependency |
| Column 2 — Narrator/Stakeholders/Coverage | `narrator`, `stakeholder_cards`, `coverage_line` | Unchanged components, relocated position only (Decision 4) |
| Column 3 — Churn Risk Overview | `score_block: ScoreBlock`, `contribution_bars: ContributionBar[]` | `trend` chart gains `XAxis`/labeled `YAxis` (Decision 7); score number sizing/color increases, same `band`-keyed palette |
| Column 3 — Action & Draft Hub | `contribution_bars: ContributionBar[]` only (unchanged from 012's Decision 3/4/8) | Selecting a row calls `openEvidence(score_contribution_id)`, now opening the centered Dialog |
| Detail modal | `EvidencePanel`/`DraftComposerPanel`'s existing data hooks (`useEvidence`, `postDraft`), unchanged | Only the outer container changes, from right-docked `<div>` to `Dialog`/`DialogContent` |

## State transitions

None new. `DashboardResponse.state` (`DashboardStateKind`) is untouched and governs
rendering exactly as it does today (FR-017); only the `normal`-state markup's column
arrangement changes.

## Validation rules

None new. `event_type` is a `NOT NULL` Postgres enum column already validated at write time
by the ingestion pipeline (`data-base/10-ddl-appendix.md`); this feature only reads it.

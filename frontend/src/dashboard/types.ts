// Mirrors contracts/dashboard.md's full DashboardResponse shape
// (architecture/07-api-spec.md) — feature 006 fills in every field feature
// 002's shell left absent.

export type Band = 'healthy' | 'watch' | 'at_risk'

export type DashboardStateKind =
  | 'no_profile'
  | 'source_down'
  | 'unresolved_person'
  | 'catching_up'
  | 'learning'
  | 'healthy_quiet'
  | 'normal'

export interface ClientHeader {
  client_name: string
  band: Band | null
  days_to_renewal: number | null
}

export interface ScoreBlock {
  score: number
  band: Band
  trend: number[]
}

export interface ContributionBar {
  score_contribution_id: string
  label: string
  points: number
  is_positive: boolean
}

// specs/016-dashboard-mockup-v2-refinement, data-model.md — the closed,
// 7-value `events.event_type` enum, surfaced through the API for the first
// time (FR-006). No 8th value is representable at the type level (P10 —
// no speculative extensibility for a category the product doesn't have).
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
  event_type: SignalType
  severity: 'info' | 'watch' | 'at_risk'
  quoted_text: string | null
  score_contribution_id: string
}

export interface StakeholderCard {
  stakeholder_id: string | null
  name: string
  role: string
  tone_trajectory: 'stable' | 'deteriorating' | 'improving' | 'unknown'
  last_seen_at: string | null
  status: 'active' | 'quiet' | 'unresolved_identity'
}

export interface CoverageLine {
  sources_read: number
  sources_expected: number
  complete_to: string | null
  status: 'ok' | 'degraded' | 'disconnected'
}

// specs/008-narrator-and-ask-agent — contracts/dashboard.md.
export interface NarratorReason {
  text: string
  points: number
  evidence_event_ids: string[]
}

export interface NarratorAction {
  text: string
  owner: string
  due_date: string
}

export interface NarratorSummary {
  headline: string
  reasons: NarratorReason[]
  actions: NarratorAction[]
}

export interface DashboardResponse {
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

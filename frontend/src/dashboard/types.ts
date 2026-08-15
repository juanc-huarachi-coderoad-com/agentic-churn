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

export interface PulseEvent {
  event_id: string
  occurred_at: string
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

export interface DashboardResponse {
  client_header: ClientHeader | null
  state: DashboardStateKind
  message: string | null
  score_block: ScoreBlock | null
  contribution_bars: ContributionBar[]
  pulse_timeline: PulseEvent[]
  stakeholder_cards: StakeholderCard[]
  coverage_line: CoverageLine | null
}

// Mirrors contracts/evidence.md's EvidenceTraceResponse
// (architecture/07-api-spec.md).

export interface QuotedMessage {
  event_id: string
  text: string | null
  occurred_at: string
}

export interface EvidenceTraceResponse {
  finding_id: string
  finding_type: string
  points: number
  baseline_value: string
  current_value: string
  what_changed: string[]
  quoted_messages: QuotedMessage[]
  arithmetic_explanation: string
}

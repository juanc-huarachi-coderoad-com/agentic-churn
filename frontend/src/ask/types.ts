// specs/008-narrator-and-ask-agent — contracts/ask.md, architecture/07-api-spec.md.

export type AskComponentType =
  | 'delta_breakdown'
  | 'baseline_comparison'
  | 'stakeholder_cards'
  | 'ranked_issues'
  | 'action_checklist'
  | 'commitments_status'
  | 'filtered_timeline'
  | 'draft_handoff'

export interface AskComponentResponse {
  intent: string
  component: AskComponentType
  component_props: Record<string, unknown>
}

export type DeclinedReason =
  'prediction' | 'colleague_judgment' | 'source_not_connected' | 'insufficient_history' | 'unclear'

export interface AskFallbackResponse {
  fallback_text: string
  sources: string[]
  declined_reason: DeclinedReason | null
}

export type AskResponse = AskComponentResponse | AskFallbackResponse

export function isComponentResponse(response: AskResponse): response is AskComponentResponse {
  return 'component' in response
}

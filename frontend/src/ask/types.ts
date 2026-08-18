// specs/008-narrator-and-ask-agent — contracts/ask.md, architecture/07-api-spec.md.
// specs/014-ask-agent-response-formats — the answered response is now an
// ordered `parts` sequence instead of one flat component shape.

export type AskComponentType =
  | 'delta_breakdown'
  | 'baseline_comparison'
  | 'stakeholder_cards'
  | 'ranked_issues'
  | 'action_checklist'
  | 'commitments_status'
  | 'filtered_timeline'
  | 'draft_handoff'

export interface TextPart {
  type: 'text'
  markdown: string
}

export interface ComponentResponsePart {
  type: 'component'
  component: AskComponentType
  component_props: Record<string, unknown>
}

export type ResponsePart = TextPart | ComponentResponsePart

export interface AskAnsweredResponse {
  intent: string
  parts: ResponsePart[]
}

export type DeclinedReason =
  'prediction' | 'colleague_judgment' | 'source_not_connected' | 'insufficient_history' | 'unclear'

export interface AskFallbackResponse {
  fallback_text: string
  sources: string[]
  declined_reason: DeclinedReason | null
}

export type AskResponse = AskAnsweredResponse | AskFallbackResponse

export function isAnsweredResponse(response: AskResponse): response is AskAnsweredResponse {
  return 'parts' in response
}

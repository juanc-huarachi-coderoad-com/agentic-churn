// specs/009-draft-composer — contracts/drafts.md, architecture/07-api-spec.md.

export type ToneVariant = 'direct' | 'formal' | 'brief'

export interface DraftRequest {
  issue_id: string
  stakeholder_id: string
  tone_variant: ToneVariant
}

export interface DraftResponse {
  id: string
  draft_text: string
  tone_variant: ToneVariant
  evidence_event_ids: string[]
  checks_passed: boolean
}

// No `is_call`/`talking_points` field (research.md Decision 8) — the
// call-not-email case is ordinary `draft_text` content.

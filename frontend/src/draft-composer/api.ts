import { apiFetch } from '../auth/api-client'
import type { DraftRequest, DraftResponse } from './types'

export class DraftCheckFailedError extends Error {}

export async function postDraft(request: DraftRequest): Promise<DraftResponse> {
  const response = await apiFetch('/api/drafts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (response.status === 422) {
    // The exact generic failure message architecture/06-error-handling.md
    // already defines for this component — never a message naming which
    // of the five checks failed (Clarifications, 2026-08-16).
    throw new DraftCheckFailedError("Couldn't generate a draft — try again")
  }
  if (!response.ok) {
    throw new Error(`Draft request failed: ${response.status}`)
  }
  return (await response.json()) as DraftResponse
}

export async function copyDraft(draftId: string): Promise<void> {
  const response = await apiFetch(`/api/drafts/${draftId}/copy`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(`Copy draft failed: ${response.status}`)
  }
}

export async function logDraftAsSent(draftId: string): Promise<void> {
  const response = await apiFetch(`/api/drafts/${draftId}/log-as-sent`, { method: 'POST' })
  if (!response.ok) {
    throw new Error(`Log-as-sent failed: ${response.status}`)
  }
}

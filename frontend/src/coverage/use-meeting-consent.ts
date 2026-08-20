import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../auth/api-client'
import type { ConsentListResponse, ConsentRequest } from './types'

async function fetchConsent(): Promise<ConsentListResponse> {
  const response = await apiFetch('/api/meeting-audio/consent')
  if (!response.ok) {
    throw new Error(`Consent request failed: ${response.status}`)
  }
  return (await response.json()) as ConsentListResponse
}

export function useMeetingConsent() {
  return useQuery({ queryKey: ['meeting-audio-consent'], queryFn: fetchConsent })
}

interface RecordConsentError extends Error {
  status: number
  detail: unknown
}

async function recordConsent(values: ConsentRequest): Promise<void> {
  const response = await apiFetch('/api/meeting-audio/consent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values),
  })
  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as { detail?: unknown } | null
    // 403 here means the signed-in account isn't a CS lead (FR-016) — this app has
    // no client-side knowledge of the current user's role to pre-hide the form with
    // (auth-store.ts only ever stores the bearer token), so the backend's RBAC gate
    // is the only enforcement point, exactly like every other write-capable form in
    // this codebase (profile-editor-form.tsx renders unconditionally too) — this
    // mutation's error state is what surfaces that outcome to the user.
    const error = new Error(`Consent submission failed: ${response.status}`) as RecordConsentError
    error.status = response.status
    error.detail = detail?.detail ?? null
    throw error
  }
}

// Mirrors use-profile.ts's useSubmitProfile — invalidates the consent list on
// success so the panel reflects the just-recorded decision immediately.
export function useRecordConsent() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: recordConsent,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['meeting-audio-consent'] })
    },
  })
}

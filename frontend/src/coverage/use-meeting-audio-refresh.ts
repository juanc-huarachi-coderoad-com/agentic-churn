import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../auth/api-client'

// Mirrors contracts/meeting-audio.md's POST /api/meeting-audio/refresh
// response shape (specs/019-meeting-audio-ingestion, User Story 3).
export interface AudioRefreshResult {
  recordings_found: number
  transcribed: number
  skipped_no_consent: number
  failed: number
  coverage_report_id: string
  source_error: string | null
}

interface RefreshError extends Error {
  status: number
}

async function refreshMeetingAudio(): Promise<AudioRefreshResult> {
  const response = await apiFetch('/api/meeting-audio/refresh', { method: 'POST' })
  if (!response.ok) {
    const error = new Error(`Refresh failed: ${response.status}`) as RefreshError
    error.status = response.status
    throw error
  }
  return (await response.json()) as AudioRefreshResult
}

// On-demand collection cycle ahead of a scheduled poll (FR-002) — the same
// trust boundary the consent mutation already relies on (backend-enforced
// 403 for a non-CS-lead, this app has no client-side role to hide the
// button with). Invalidates coverage on success since a successful refresh
// can change source health (User Story 4).
export function useRefreshMeetingAudio() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: refreshMeetingAudio,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['coverage'] })
    },
  })
}

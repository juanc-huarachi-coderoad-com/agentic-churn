import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../auth/api-client'
import type { ProfileFormValues } from './schema'
import type { ProfileResponse } from './types'

async function fetchProfile(): Promise<ProfileResponse> {
  const response = await apiFetch('/api/profile')
  if (!response.ok) {
    throw new Error(`Profile request failed: ${response.status}`)
  }
  return (await response.json()) as ProfileResponse
}

export function useProfile() {
  return useQuery({ queryKey: ['profile'], queryFn: fetchProfile })
}

interface SubmitProfileError extends Error {
  status: number
  detail: unknown
}

async function submitProfile(values: ProfileFormValues): Promise<ProfileResponse> {
  const response = await apiFetch('/api/profile', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(values),
  })
  if (!response.ok) {
    const detail = (await response.json().catch(() => null)) as { detail?: unknown } | null
    const error = new Error(`Profile submission failed: ${response.status}`) as SubmitProfileError
    error.status = response.status
    error.detail = detail?.detail ?? null
    throw error
  }
  return (await response.json()) as ProfileResponse
}

// specs/011-production-hardening, User Story 5 — invalidates the profile query
// on success so the form re-loads the just-created version_number, matching
// use-feedback.ts's own invalidate-on-success pattern from feature 010.
export function useSubmitProfile() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: submitProfile,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['profile'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

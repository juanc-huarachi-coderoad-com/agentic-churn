import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../auth/api-client'
import type { EvidenceTraceResponse } from './types'

async function fetchEvidence(scoreContributionId: string): Promise<EvidenceTraceResponse> {
  const response = await apiFetch(`/api/evidence/${scoreContributionId}`)
  if (!response.ok) {
    throw new Error(`Evidence request failed: ${response.status}`)
  }
  return (await response.json()) as EvidenceTraceResponse
}

// `scoreContributionId: null` means "panel closed" — `enabled: false` skips
// the fetch entirely rather than firing a request for a `null` id.
export function useEvidence(scoreContributionId: string | null) {
  return useQuery({
    queryKey: ['evidence', scoreContributionId],
    queryFn: () => fetchEvidence(scoreContributionId as string),
    enabled: scoreContributionId !== null,
  })
}

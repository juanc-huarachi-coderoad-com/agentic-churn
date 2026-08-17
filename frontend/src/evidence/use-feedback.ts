import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from '../auth/api-client'

export type Verdict = 'correct' | 'false_alarm' | 'resolved'

interface SubmitFeedbackInput {
  findingId: string
  verdict: Verdict
}

async function submitFeedback({ findingId, verdict }: SubmitFeedbackInput): Promise<void> {
  const response = await apiFetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ finding_id: findingId, verdict }),
  })
  if (!response.ok) {
    throw new Error(`Feedback request failed: ${response.status}`)
  }
}

// One click, no modal, no confirmation toast (FR-002) — invalidates the
// evidence query on success so the panel re-fetches and picks up the
// pattern's new disclosure_text, matching use-evidence.ts's own query key.
export function useFeedback(scoreContributionId: string | null) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: submitFeedback,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidence', scoreContributionId] })
    },
  })
}

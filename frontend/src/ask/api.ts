import { apiFetch } from '../auth/api-client'
import type { AskResponse } from './types'

export async function postAsk(question: string): Promise<AskResponse> {
  const response = await apiFetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  })
  if (!response.ok) {
    throw new Error(`Ask request failed: ${response.status}`)
  }
  return (await response.json()) as AskResponse
}

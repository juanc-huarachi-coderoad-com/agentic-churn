import { apiFetch } from '../auth/api-client'
import type { AskResponse, HistoryTurn } from './types'

export interface PostAskPayload {
  question: string
  // specs/017-assistant-chat-conversation — up to the 5 most recent prior
  // exchanges, resent verbatim (contracts/ask.md). Optional/empty for a
  // conversation's first question.
  history?: HistoryTurn[]
}

export async function postAsk({ question, history = [] }: PostAskPayload): Promise<AskResponse> {
  const response = await apiFetch('/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, history }),
  })
  if (!response.ok) {
    throw new Error(`Ask request failed: ${response.status}`)
  }
  return (await response.json()) as AskResponse
}

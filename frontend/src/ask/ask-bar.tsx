import { useMutation } from '@tanstack/react-query'
import { Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Icon } from '../components/ui/icon'
import { postAsk } from './api'
import { AnswerRenderer } from './components/answer-renderer'
import { isAnsweredResponse } from './types'

type AskBarState = 'idle' | 'thinking' | 'answered'

interface AskBarProps {
  onOpenDraftComposer?: (issueId: string, stakeholderId: string) => void
  onOpenEvidence?: (scoreContributionId: string) => void
}

// specs/008-narrator-and-ask-agent — Idle/Thinking/Answered (REQ-M8-02).
// Never recomputes anything itself — every answer is exactly what POST
// /api/ask returned.
//
// specs/016-dashboard-mockup-v2-refinement (FR-004, SC-007): a permanently
// docked, already-expanded panel in column 1, directly below the AURA risk
// indicator — supersedes 012's floating, collapse-by-default launcher
// (research.md Decision 5's sibling change, spec.md Assumptions). No
// isOpen/launcher state exists anymore; the mutation (and therefore the
// current exchange) lives in this same always-mounted component, so
// scrolling or interacting elsewhere on the dashboard never discards it
// (Acceptance Scenario 2).
export function AskBar({ onOpenDraftComposer, onOpenEvidence }: AskBarProps) {
  const [question, setQuestion] = useState('')
  const mutation = useMutation({ mutationFn: postAsk })

  const state: AskBarState = mutation.isPending
    ? 'thinking'
    : mutation.isSuccess || mutation.isError
      ? 'answered'
      : 'idle'

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    if (!question.trim()) return
    mutation.mutate(question)
  }

  return (
    <div
      className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-sm"
      data-state={state}
      data-testid="ask-bar"
    >
      <div className="flex items-center gap-2 border-b border-neutral-100 px-4 py-3">
        <Icon icon={Sparkles} size={16} className="text-neutral-500" />
        <span className="text-sm font-medium text-neutral-900">Aura Assistant</span>
        <span
          className="ml-auto flex items-center gap-1.5 text-xs text-neutral-400"
          aria-hidden="true"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
          Online
        </span>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-3">
        {state === 'answered' && (
          <div className="rounded-md border border-neutral-100 bg-neutral-50 p-4">
            {mutation.isError && (
              <p className="text-sm text-red-600">
                That's taking longer than it should — try again, or check the dashboard directly.
              </p>
            )}
            {mutation.data &&
              (isAnsweredResponse(mutation.data) ? (
                <AnswerRenderer
                  answer={mutation.data}
                  onOpenDraftComposer={onOpenDraftComposer}
                  onOpenEvidence={onOpenEvidence}
                />
              ) : (
                <div>
                  <p className="text-sm text-neutral-700">{mutation.data.fallback_text}</p>
                  <p className="mt-1 text-xs text-neutral-400">Fallback answer</p>
                </div>
              ))}
          </div>
        )}
        {state === 'idle' && <p className="text-sm text-neutral-400">Ask about this account…</p>}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-neutral-100 p-3">
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about this account…"
          aria-label="Ask a question"
          disabled={state === 'thinking'}
          className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
        />
        <button
          type="submit"
          disabled={state === 'thinking'}
          className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {state === 'thinking' ? 'Thinking…' : 'Ask'}
        </button>
      </form>
    </div>
  )
}

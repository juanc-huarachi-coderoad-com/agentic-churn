import { useMutation } from '@tanstack/react-query'
import { Sparkles, X } from 'lucide-react'
import { useState } from 'react'
import { Icon } from '../components/ui/icon'
import { postAsk } from './api'
import { AnswerRenderer } from './components/answer-renderer'
import { isComponentResponse } from './types'

type AskBarState = 'idle' | 'thinking' | 'answered'

interface AskBarProps {
  onOpenDraftComposer?: (issueId: string, stakeholderId: string) => void
  onOpenEvidence?: (scoreContributionId: string) => void
}

// specs/008-narrator-and-ask-agent — Idle/Thinking/Answered (REQ-M8-02).
// Never recomputes anything itself — every answer is exactly what POST
// /api/ask returned.
//
// specs/012-dashboard-visual-redesign (FR-007, Clarifications 2026-08-17):
// presented as a floating, collapsible component instead of an always-
// present bottom bar — starts collapsed on every mount. `isOpen` is local
// UI-only state; the mutation itself (and therefore the current exchange)
// lives in this same component regardless of isOpen, so collapsing and
// reopening never discards it (FR-008).
export function AskBar({ onOpenDraftComposer, onOpenEvidence }: AskBarProps) {
  const [isOpen, setIsOpen] = useState(false)
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

  if (!isOpen) {
    return (
      <div data-state={state} data-testid="ask-bar">
        <button
          type="button"
          onClick={() => setIsOpen(true)}
          aria-label="Open assistant"
          className="fixed right-6 bottom-6 z-40 flex h-14 w-14 items-center justify-center rounded-full bg-neutral-900 text-white shadow-lg hover:bg-neutral-800"
        >
          <Icon icon={Sparkles} size={22} aria-hidden={false} />
        </button>
      </div>
    )
  }

  return (
    <div
      className="fixed right-6 bottom-6 z-40 flex max-h-[32rem] w-96 flex-col overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-xl"
      data-state={state}
      data-testid="ask-bar"
    >
      <div className="flex items-center justify-between border-b border-neutral-100 px-4 py-3">
        <span className="flex items-center gap-2 text-sm font-medium text-neutral-900">
          <Icon icon={Sparkles} size={16} className="text-neutral-500" />
          Aura Assistant
        </span>
        <button
          type="button"
          onClick={() => setIsOpen(false)}
          aria-label="Collapse assistant"
          className="text-neutral-400 hover:text-neutral-600"
        >
          <Icon icon={X} size={18} aria-hidden={false} />
        </button>
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
              (isComponentResponse(mutation.data) ? (
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

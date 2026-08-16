import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { postAsk } from './api'
import { AnswerRenderer } from './components/answer-renderer'
import { isComponentResponse } from './types'

type AskBarState = 'idle' | 'thinking' | 'answered'

// specs/008-narrator-and-ask-agent — always present, bottom of screen
// (base/...md §11.3), Idle/Thinking/Answered (REQ-M8-02). Never recomputes
// anything itself — every answer is exactly what POST /api/ask returned.
export function AskBar() {
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
      className="fixed inset-x-0 bottom-0 z-40 border-t border-neutral-200 bg-white"
      data-state={state}
      data-testid="ask-bar"
    >
      <div className="mx-auto max-w-3xl px-4 py-3">
        {state === 'answered' && (
          <div className="mb-3 max-h-64 overflow-y-auto rounded-md border border-neutral-100 bg-neutral-50 p-4">
            {mutation.isError && (
              <p className="text-sm text-red-600">
                That's taking longer than it should — try again, or check the dashboard directly.
              </p>
            )}
            {mutation.data &&
              (isComponentResponse(mutation.data) ? (
                <AnswerRenderer answer={mutation.data} />
              ) : (
                <div>
                  <p className="text-sm text-neutral-700">{mutation.data.fallback_text}</p>
                  <p className="mt-1 text-xs text-neutral-400">Fallback answer</p>
                </div>
              ))}
          </div>
        )}

        <form onSubmit={handleSubmit} className="flex gap-2">
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
    </div>
  )
}

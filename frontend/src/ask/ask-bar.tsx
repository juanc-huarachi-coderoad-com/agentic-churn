import { useMutation } from '@tanstack/react-query'
import { Sparkles, User } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Icon } from '../components/ui/icon'
import { postAsk } from './api'
import { AnswerRenderer } from './components/answer-renderer'
import { isAnsweredResponse } from './types'
import type { AskResponse, HistoryTurn, Turn } from './types'

type AskBarState = 'idle' | 'thinking' | 'answered'

interface AskBarProps {
  onOpenDraftComposer?: (issueId: string, stakeholderId: string) => void
  onOpenEvidence?: (scoreContributionId: string) => void
}

const MAX_HISTORY_TURNS = 5

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
//
// specs/017-assistant-chat-conversation — a real multi-turn conversation:
// `turns` is an append-only, in-memory transcript (research.md Decision 1 —
// component state, not a global store; no persistence, no per-account
// keying, since this product has exactly one account per deployment,
// research.md Decision 0). Sending is single-flight (research.md Decision
// 6): the send control is disabled while any turn is pending, but typing
// stays enabled the whole time.
export function AskBar({ onOpenDraftComposer, onOpenEvidence }: AskBarProps) {
  const [question, setQuestion] = useState('')
  const [turns, setTurns] = useState<Turn[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)
  const mutation = useMutation({ mutationFn: postAsk })

  const isPending = turns.some((turn) => turn.status === 'pending')
  const state: AskBarState = isPending ? 'thinking' : turns.length > 0 ? 'answered' : 'idle'

  useEffect(() => {
    const container = scrollRef.current
    if (container) container.scrollTop = container.scrollHeight
  }, [turns.length])

  function updateTurn(id: string, patch: Partial<Turn>) {
    setTurns((prev) => prev.map((turn) => (turn.id === id ? { ...turn, ...patch } : turn)))
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || isPending) return

    const id = crypto.randomUUID()
    const history: HistoryTurn[] = turns
      .filter((turn): turn is Turn & { response: AskResponse } => turn.status === 'answered' && turn.response !== null)
      .slice(-MAX_HISTORY_TURNS)
      .map((turn) => ({ question: turn.question, answer: turn.response }))

    setTurns((prev) => [
      ...prev,
      {
        id,
        question: trimmed,
        status: 'pending',
        response: null,
        error: null,
        questionSentAt: new Date().toISOString(),
        respondedAt: null,
      },
    ])
    setQuestion('')

    mutation.mutate(
      { question: trimmed, history },
      {
        onSuccess: (data) =>
          updateTurn(id, { status: 'answered', response: data, respondedAt: new Date().toISOString() }),
        onError: () =>
          updateTurn(id, {
            status: 'error',
            error: "That's taking longer than it should — try again, or check the dashboard directly.",
            respondedAt: new Date().toISOString(),
          }),
      },
    )
  }

  return (
    <div
      className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-lg border border-neutral-200 bg-white shadow-sm"
      data-state={state}
      data-testid="ask-bar"
    >
      <div className="flex items-center gap-2 border-b border-neutral-100 px-4 py-3">
        <Icon icon={Sparkles} size={16} className="text-violet-500" />
        <span className="text-sm font-medium text-neutral-900">Aura Assistant</span>
        <span
          className="ml-auto flex items-center gap-1.5 text-xs text-neutral-400"
          aria-hidden="true"
        >
          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
          Online
        </span>
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3">
        {turns.length === 0 ? (
          <p className="text-sm text-neutral-400">Ask about this account…</p>
        ) : (
          <div className="space-y-4">
            {turns.map((turn) => (
              <TurnView
                key={turn.id}
                turn={turn}
                onOpenDraftComposer={onOpenDraftComposer}
                onOpenEvidence={onOpenEvidence}
              />
            ))}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex gap-2 border-t border-neutral-100 p-3">
        <input
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about this account…"
          aria-label="Ask a question"
          className="flex-1 rounded-md border border-neutral-200 px-3 py-2 text-sm focus:border-neutral-400 focus:outline-none"
        />
        <button
          type="submit"
          disabled={isPending}
          className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {isPending ? 'Thinking…' : 'Ask'}
        </button>
      </form>
    </div>
  )
}

interface TurnViewProps {
  turn: Turn
  onOpenDraftComposer?: (issueId: string, stakeholderId: string) => void
  onOpenEvidence?: (scoreContributionId: string) => void
}

// specs/021-chat-component-redesign — research.md Decision 3: the two fixed
// sender identities rendered on every completed message, matching
// base/chatComponent.jpg (generic person icon for the human, sparkle for
// AURA Assistant). Never personalized per logged-in user (FR-006).
const HUMAN_PARTICIPANT = { icon: User, label: 'Human' } as const
const ASSISTANT_PARTICIPANT = { icon: Sparkles, label: 'AURA Assistant' } as const

// specs/021-chat-component-redesign — research.md Decision 1: renders an
// ISO 8601 timestamp as the 12-hour "10:32 AM" style required by FR-003.
function formatMessageTime(iso: string): string {
  return new Intl.DateTimeFormat(undefined, {
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  }).format(new Date(iso))
}

// specs/017-assistant-chat-conversation — one turn's question plus whatever
// it resolved to (pending/answered/error). `AnswerRenderer` is invoked once
// per answered turn, so every turn in the growing transcript keeps its own
// independent mixed text/generative-UI rendering (FR-011), not just the
// latest one.
function TurnView({ turn, onOpenDraftComposer, onOpenEvidence }: TurnViewProps) {
  return (
    <div className="space-y-2" data-testid="turn" data-status={turn.status}>
      <div
        className="flex items-center gap-1.5 text-xs text-neutral-500"
        data-testid="human-identity-row"
      >
        <span data-testid="sender-icon-human">
          <Icon icon={HUMAN_PARTICIPANT.icon} size={14} className="text-violet-500" />
        </span>
        <span className="font-medium text-neutral-700">{HUMAN_PARTICIPANT.label}</span>
        <span>{formatMessageTime(turn.questionSentAt)}</span>
      </div>
      <div className="rounded-md border border-violet-100 bg-violet-50 px-4 py-3">
        <p className="text-sm font-medium text-neutral-900">{turn.question}</p>
      </div>
      {turn.status === 'pending' && (
        <p className="text-sm text-neutral-400" data-testid="turn-thinking">
          Thinking…
        </p>
      )}
      {turn.status === 'error' && <p className="text-sm text-red-600">{turn.error}</p>}
      {turn.status === 'answered' && turn.response && turn.respondedAt && (
        <div className="space-y-2">
          <div
            className="flex items-center justify-end gap-1.5 text-xs text-neutral-500"
            data-testid="assistant-identity-row"
          >
            <span>{formatMessageTime(turn.respondedAt)}</span>
            <span className="font-medium text-neutral-700">{ASSISTANT_PARTICIPANT.label}</span>
            <span data-testid="sender-icon-assistant">
              <Icon icon={ASSISTANT_PARTICIPANT.icon} size={14} className="text-violet-500" />
            </span>
          </div>
          <div className="rounded-md border border-neutral-100 bg-neutral-50 p-4">
            {isAnsweredResponse(turn.response) ? (
              <AnswerRenderer
                answer={turn.response}
                onOpenDraftComposer={onOpenDraftComposer}
                onOpenEvidence={onOpenEvidence}
              />
            ) : (
              <div>
                <p className="text-sm text-neutral-700">{turn.response.fallback_text}</p>
                {/* specs/017-assistant-chat-conversation (research.md Decision
                    5): declined_reason is null only for a recognized
                    greeting/thanks/capabilities reply — a real decline always
                    has a non-null reason and keeps this caption. */}
                {turn.response.declined_reason !== null && (
                  <p className="mt-1 text-xs text-neutral-400">Fallback answer</p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

import type { PulseEvent } from './types'

const SEVERITY_DOT_CLASS: Record<PulseEvent['severity'], string> = {
  info: 'bg-neutral-300',
  watch: 'bg-amber-500',
  at_risk: 'bg-red-500',
}

interface PulseTimelineProps {
  events: PulseEvent[]
  onSelect: (scoreContributionId: string) => void
}

export function PulseTimeline({ events, onSelect }: PulseTimelineProps) {
  if (events.length === 0) {
    return null
  }

  return (
    <ul className="mt-6 space-y-3">
      {events.map((event) => (
        <li key={event.event_id}>
          <button
            type="button"
            onClick={() => onSelect(event.score_contribution_id)}
            className="flex w-full items-start gap-3 text-left"
          >
            <span
              className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${SEVERITY_DOT_CLASS[event.severity]}`}
              aria-hidden="true"
            />
            <span className="flex-1">
              {event.quoted_text && (
                // Client-authored words render serif, as quotes — never
                // conflated with system-generated text (REQ-M8-04).
                <span className="font-serif text-sm text-neutral-800">
                  &ldquo;{event.quoted_text}&rdquo;
                </span>
              )}
              <span className="block text-xs text-neutral-400">
                {new Date(event.occurred_at).toLocaleString()}
              </span>
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

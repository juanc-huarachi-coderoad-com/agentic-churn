import { AlertTriangle, Info, TrendingUp } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Icon } from '../components/ui/icon'
import { cn } from '../lib/utils'
import type { PulseEvent } from './types'

const SEVERITY_ICON: Record<PulseEvent['severity'], LucideIcon> = {
  info: Info,
  watch: TrendingUp,
  at_risk: AlertTriangle,
}

const SEVERITY_RING_CLASS: Record<PulseEvent['severity'], string> = {
  info: 'border-neutral-300 text-neutral-400',
  watch: 'border-amber-300 text-amber-600',
  at_risk: 'border-red-300 text-red-600',
}

interface PulseTimelineProps {
  events: PulseEvent[]
  onSelect: (scoreContributionId: string) => void
}

function relativeTime(occurredAt: string): string {
  const diffMs = Date.now() - new Date(occurredAt).getTime()
  const minutes = Math.round(diffMs / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.round(hours / 24)
  return `${days}d ago`
}

// Restyled as "The Signal Stream" (base/mockup-mainPage.jpg) — same props,
// same event data, same onSelect → EvidencePanel wiring as before this
// feature; only the markup changed.
export function PulseTimeline({ events, onSelect }: PulseTimelineProps) {
  if (events.length === 0) {
    return null
  }

  return (
    <ul className="space-y-4">
      {events.map((event) => (
        <li key={event.event_id}>
          <button
            type="button"
            onClick={() => onSelect(event.score_contribution_id)}
            className="flex w-full items-start gap-3 rounded-lg border border-neutral-200 bg-white p-4 text-left transition-colors hover:border-neutral-300"
          >
            <span
              className={cn(
                'mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2',
                SEVERITY_RING_CLASS[event.severity],
              )}
              aria-hidden="true"
            >
              <Icon icon={SEVERITY_ICON[event.severity]} size={14} />
            </span>
            <span className="min-w-0 flex-1">
              <span className="block text-xs text-neutral-400">
                {relativeTime(event.occurred_at)}
              </span>
              {event.quoted_text && (
                // Client-authored words render serif, as quotes — never
                // conflated with system-generated text (REQ-M8-04).
                <span className="mt-1 block font-serif text-sm text-neutral-800">
                  &ldquo;{event.quoted_text}&rdquo;
                </span>
              )}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

import { HelpCircle } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Icon } from '../components/ui/icon'
import { cn } from '../lib/utils'
import { TYPE_ICON, TYPE_LABEL } from './signal-type'
import type { PulseEvent } from './types'

const SEVERITY_RING_CLASS: Record<PulseEvent['severity'], string> = {
  info: 'border-neutral-300 text-neutral-400',
  watch: 'border-amber-300 text-amber-600',
  at_risk: 'border-red-300 text-red-600',
}

// spec.md Edge Cases / US3 Acceptance Scenario 3: an event_type without a
// defined mapping (e.g. a new type added to the database later, outside
// this closed union at runtime) still renders — a sensible fallback, never
// a broken stream.
const FALLBACK_ICON: LucideIcon = HelpCircle
const FALLBACK_LABEL = 'Signal'

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

// Restyled as "The Signal Stream" (base/mockup-mainPage-v2.jpg) — same
// onSelect → EvidencePanel wiring as before this feature; the markup now
// carries a dual-channel icon (FR-005a: shape from the entry's real
// event_type, color/ring from its severity) and a connecting vertical
// timeline line between consecutive entries (FR-007).
export function PulseTimeline({ events, onSelect }: PulseTimelineProps) {
  if (events.length === 0) {
    return null
  }

  return (
    <ul>
      {events.map((event, index) => {
        const TypeIcon = TYPE_ICON[event.event_type] ?? FALLBACK_ICON
        const typeLabel = TYPE_LABEL[event.event_type] ?? FALLBACK_LABEL
        const isLast = index === events.length - 1

        return (
          <li key={event.event_id} className="relative">
            {!isLast && (
              <span
                data-testid="pulse-connector"
                aria-hidden="true"
                className="absolute top-9 left-[1.15rem] h-[calc(100%-0.5rem)] w-px bg-neutral-200"
              />
            )}
            <button
              type="button"
              onClick={() => onSelect(event.score_contribution_id)}
              className="group relative z-10 mb-4 flex w-full items-start gap-3 rounded-lg border border-transparent bg-white p-3 text-left transition-all duration-150 hover:border-neutral-200 hover:bg-neutral-50 hover:shadow-sm"
            >
              <span
                data-testid={`pulse-icon-${event.event_id}`}
                data-icon-type={event.event_type}
                className={cn(
                  'mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 bg-white transition-transform duration-150 group-hover:scale-110',
                  SEVERITY_RING_CLASS[event.severity],
                )}
                aria-hidden="true"
              >
                <Icon icon={TypeIcon} size={16} />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block text-xs text-neutral-400">
                  {relativeTime(event.occurred_at)} · {typeLabel}
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
        )
      })}
    </ul>
  )
}

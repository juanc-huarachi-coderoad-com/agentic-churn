import { cn } from '../lib/utils'
import type { ConnectorStatus } from './types'

const STATUS_LABEL: Record<ConnectorStatus, string> = {
  live: 'Live',
  simulated: 'Simulated',
  planned: 'Planned',
}

// FR-008: status is conveyed by this text label, never by color alone — the
// color classes below are reinforcement, not the only signal.
const STATUS_CLASS: Record<ConnectorStatus, string> = {
  live: 'bg-emerald-50 text-emerald-700',
  simulated: 'bg-blue-50 text-blue-700',
  planned: 'bg-violet-50 text-violet-700',
}

interface StatusBadgeProps {
  status: ConnectorStatus
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium',
        STATUS_CLASS[status],
        className,
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  )
}

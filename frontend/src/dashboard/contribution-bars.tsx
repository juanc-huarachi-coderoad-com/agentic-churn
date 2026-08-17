import type { ContributionBar } from './types'

// Reuses the same red/amber rule the backend's pulse_severity() already
// applies (research.md's Decision) — never a naive "negative = red".
const AT_RISK_FINDING_TYPES = new Set(['broken_response_promise', 'contact_absence'])

function barColorClass(bar: ContributionBar): string {
  if (bar.is_positive) return 'bg-green-500'
  if (AT_RISK_FINDING_TYPES.has(bar.label)) return 'bg-red-500'
  return 'bg-amber-500'
}

interface ContributionBarsProps {
  bars: ContributionBar[]
  onSelect: (scoreContributionId: string) => void
}

export function ContributionBars({ bars, onSelect }: ContributionBarsProps) {
  if (bars.length === 0) {
    // REQ-M8-02: empty when healthy — an honest empty state, not a "no data"
    // placeholder (base/...md §11.3).
    return null
  }

  const max = Math.max(...bars.map((bar) => Math.abs(bar.points)), 1)

  return (
    <ul className="mt-3 space-y-2">
      {bars.map((bar) => {
        // Display-only sign: is_positive already means "reduces risk" (see
        // barColorClass above) — this just formats the same points value the
        // way the mockup does ("+25"/"-8"), never a different number.
        const signedPoints = bar.is_positive ? -Math.abs(bar.points) : Math.abs(bar.points)
        return (
          <li key={bar.score_contribution_id}>
            <button
              type="button"
              onClick={() => onSelect(bar.score_contribution_id)}
              className="flex w-full items-center gap-3 text-left"
            >
              <span className="min-w-0 flex-1 truncate text-sm text-neutral-600">
                {bar.label.replace(/_/g, ' ')}
              </span>
              <span className="h-2 w-12 shrink-0 overflow-hidden rounded-full bg-neutral-100">
                <span
                  className={`block h-full ${barColorClass(bar)}`}
                  style={{ width: `${(Math.abs(bar.points) / max) * 100}%` }}
                />
              </span>
              <span className="w-8 shrink-0 text-right text-sm tabular-nums text-neutral-500">
                {signedPoints > 0 ? `+${signedPoints.toFixed(0)}` : signedPoints.toFixed(0)}
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

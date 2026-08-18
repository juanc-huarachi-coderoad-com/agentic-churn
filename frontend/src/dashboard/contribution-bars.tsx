import { useState } from 'react'
import { groupContributionBars, signedPoints } from './group-contribution-bars'
import type { ContributionBar } from './types'

// Reuses the same red/amber rule the backend's pulse_severity() already
// applies (research.md's Decision) — never a naive "negative = red".
const AT_RISK_FINDING_TYPES = new Set(['broken_response_promise', 'contact_absence'])

function barColorClass(bar: { label: string; is_positive: boolean }): string {
  if (bar.is_positive) return 'bg-green-500'
  if (AT_RISK_FINDING_TYPES.has(bar.label)) return 'bg-red-500'
  return 'bg-amber-500'
}

function formatPoints(points: number): string {
  return points > 0 ? `+${points.toFixed(0)}` : points.toFixed(0)
}

interface ContributionBarsProps {
  bars: ContributionBar[]
  onSelect: (scoreContributionId: string) => void
}

export function ContributionBars({ bars, onSelect }: ContributionBarsProps) {
  const [expandedLabel, setExpandedLabel] = useState<string | null>(null)

  if (bars.length === 0) {
    // REQ-M8-02: empty when healthy — an honest empty state, not a "no data"
    // placeholder (base/...md §11.3).
    return null
  }

  const groups = groupContributionBars(bars)
  const barsByLabel = new Map(bars.map((bar) => [bar.score_contribution_id, bar] as const))
  const max = Math.max(...groups.map((group) => Math.abs(group.points)), 1)

  return (
    <ul className="mt-3 space-y-2">
      {groups.map((group) => {
        const isGroup = group.contribution_ids.length > 1
        const isExpanded = expandedLabel === group.label

        return (
          <li key={group.label}>
            <button
              type="button"
              onClick={() =>
                isGroup
                  ? setExpandedLabel(isExpanded ? null : group.label)
                  : onSelect(group.contribution_ids[0])
              }
              aria-expanded={isGroup ? isExpanded : undefined}
              className="flex w-full items-center gap-3 text-left"
            >
              <span className="min-w-0 flex-1 truncate text-sm text-neutral-600">
                {group.label.replace(/_/g, ' ')}
              </span>
              {isGroup && (
                <span className="shrink-0 rounded-full bg-neutral-100 px-2 py-0.5 text-xs font-medium text-neutral-500">
                  ×{group.contribution_ids.length}
                </span>
              )}
              <span className="h-2 w-12 shrink-0 overflow-hidden rounded-full bg-neutral-100">
                <span
                  className={`block h-full ${barColorClass(group)}`}
                  style={{ width: `${(Math.abs(group.points) / max) * 100}%` }}
                />
              </span>
              <span className="w-8 shrink-0 text-right text-sm tabular-nums text-neutral-500">
                {formatPoints(group.points)}
              </span>
            </button>

            {isGroup && isExpanded && (
              <ul className="mt-2 space-y-2 pl-4">
                {group.contribution_ids.map((id) => {
                  const bar = barsByLabel.get(id)
                  if (!bar) return null
                  const points = signedPoints(bar)
                  return (
                    <li key={id}>
                      <button
                        type="button"
                        onClick={() => onSelect(id)}
                        className="flex w-full items-center gap-3 text-left"
                      >
                        <span className="min-w-0 flex-1 truncate text-xs text-neutral-400">
                          {bar.label.replace(/_/g, ' ')}
                        </span>
                        <span className="w-8 shrink-0 text-right text-xs tabular-nums text-neutral-400">
                          {formatPoints(points)}
                        </span>
                      </button>
                    </li>
                  )
                })}
              </ul>
            )}
          </li>
        )
      })}
    </ul>
  )
}

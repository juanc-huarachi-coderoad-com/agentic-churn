import { Card, CardHeader, CardTitle } from '../components/ui/card'
import { cn } from '../lib/utils'
import { PRIORITY_BADGE_CLASS, PRIORITY_LABEL, priorityTierFromPoints } from './priority-tier'
import type { ContributionBar } from './types'

interface ActionDraftHubProps {
  bars: ContributionBar[]
  onSelect: (scoreContributionId: string) => void
}

// "The Action & Draft Hub" (base/mockup-mainPage.jpg). Built from
// contribution_bars only — the one field with a real score_contribution_id
// to act on (research.md Decision 3/4/8). Selecting a row opens the same
// EvidencePanel every other contribution-bar affordance already opens; this
// is a new visual entry point onto an existing interaction, not a new one.
export function ActionDraftHub({ bars, onSelect }: ActionDraftHubProps) {
  if (bars.length === 0) {
    return null
  }

  const ranked = [...bars].sort((a, b) => Math.abs(b.points) - Math.abs(a.points))

  return (
    <Card>
      <CardHeader>
        <CardTitle>The Action &amp; Draft Hub</CardTitle>
      </CardHeader>
      <p className="mt-1 text-xs tracking-wide text-neutral-400 uppercase">Priority actions</p>
      <ol className="mt-3 space-y-2">
        {ranked.map((bar, index) => {
          const tier = priorityTierFromPoints(Math.abs(bar.points))
          return (
            <li key={bar.score_contribution_id}>
              <button
                type="button"
                onClick={() => onSelect(bar.score_contribution_id)}
                className="group flex w-full items-center gap-3 rounded-md border border-neutral-200 p-3 text-left transition-all duration-150 hover:border-neutral-300 hover:bg-neutral-50 hover:shadow-sm"
              >
                <span
                  className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-neutral-100 text-xs tabular-nums text-neutral-500 transition-transform duration-150 group-hover:scale-110"
                  aria-hidden="true"
                >
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-neutral-900">
                    {bar.label.replace(/_/g, ' ')}
                  </span>
                  <span className="block text-xs text-neutral-500">
                    {bar.is_positive ? 'Improving indicator' : 'Prioritized risk indicator'}
                  </span>
                </span>
                <span
                  className={cn(
                    'shrink-0 rounded-full px-2 py-0.5 text-xs font-medium',
                    PRIORITY_BADGE_CLASS[tier],
                  )}
                >
                  {PRIORITY_LABEL[tier]}
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </Card>
  )
}

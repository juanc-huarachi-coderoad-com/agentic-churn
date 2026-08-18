import type { ContributionBar } from './types'

export interface GroupedContributionBar {
  label: string
  points: number
  is_positive: boolean
  contribution_ids: string[]
}

// Same display-only sign flip contribution-bars.tsx used inline: is_positive
// already means "reduces risk", so it renders as a negative number.
export function signedPoints(bar: Pick<ContributionBar, 'points' | 'is_positive'>): number {
  return bar.is_positive ? -Math.abs(bar.points) : Math.abs(bar.points)
}

// Groups same-label findings (e.g. multiple "escalation language" events)
// into one row summing their net effect, while keeping every original
// score_contribution_id so each instance can still open its own evidence.
export function groupContributionBars(bars: ContributionBar[]): GroupedContributionBar[] {
  const groups = new Map<string, GroupedContributionBar>()

  for (const bar of bars) {
    const existing = groups.get(bar.label)
    if (existing) {
      existing.points += signedPoints(bar)
      existing.contribution_ids.push(bar.score_contribution_id)
    } else {
      groups.set(bar.label, {
        label: bar.label,
        points: signedPoints(bar),
        is_positive: false,
        contribution_ids: [bar.score_contribution_id],
      })
    }
  }

  const result = [...groups.values()]
  for (const group of result) {
    group.is_positive = group.points <= 0
  }

  result.sort((a, b) => Math.abs(b.points) - Math.abs(a.points))
  return result
}

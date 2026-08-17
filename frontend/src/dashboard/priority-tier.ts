export type PriorityTier = 'high' | 'medium' | 'low'

// Display-only mapping over an already-fetched points magnitude (research.md
// Decision 3, data-model.md) — mirrors the ranking dashboard-page.tsx already
// uses for topContributionId. Never persisted, never sent anywhere; changing
// these thresholds changes a badge color, never a score.
export function priorityTierFromPoints(absPoints: number): PriorityTier {
  if (absPoints >= 20) return 'high'
  if (absPoints >= 10) return 'medium'
  return 'low'
}

export const PRIORITY_LABEL: Record<PriorityTier, string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
}

export const PRIORITY_BADGE_CLASS: Record<PriorityTier, string> = {
  high: 'bg-red-100 text-red-800',
  medium: 'bg-amber-100 text-amber-800',
  low: 'bg-neutral-100 text-neutral-600',
}

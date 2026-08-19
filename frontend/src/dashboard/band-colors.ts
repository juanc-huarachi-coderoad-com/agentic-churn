import type { Band } from './types'

// Recharts (and the AURA risk orb, research.md Decision 6) need real color
// values, not Tailwind class names — these match the red-500/amber-500/
// neutral-400 the rest of the dashboard already uses for the same band.
// Extracted out of score-block.tsx (data-model.md, research.md Decision 6)
// so score-block.tsx and aura-risk-orb.tsx never drift out of sync.
export const BAND_CHART_COLOR: Record<Band, string> = {
  healthy: '#a3a3a3',
  watch: '#f59e0b',
  at_risk: '#ef4444',
}

import type { CSSProperties } from 'react'
import { BAND_CHART_COLOR } from './band-colors'
import type { Band } from './types'

interface AuraRiskOrbProps {
  score: number
  band: Band
}

// "AURA" — the gradient-colored risk indicator in the first column
// (base/mockup-mainPage-v2.jpg). Reuses the same band-keyed palette
// score-block.tsx's trend chart already uses (band-colors.ts,
// research.md Decision 6) — no new color thresholds, no continuous
// score->hue interpolation (spec.md Assumptions).
export function AuraRiskOrb({ score, band }: AuraRiskOrbProps) {
  const color = BAND_CHART_COLOR[band]

  return (
    <div
      data-testid="aura-risk-orb"
      className="relative flex aspect-square w-full items-center justify-center rounded-full"
      style={
        {
          '--orb-color': color,
          background: `radial-gradient(circle at 42% 38%, color-mix(in srgb, var(--orb-color) 70%, white), var(--orb-color) 65%, color-mix(in srgb, var(--orb-color) 60%, black) 100%)`,
          boxShadow: `0 0 60px -8px var(--orb-color)`,
        } as CSSProperties
      }
    >
      <span className="text-4xl font-semibold text-white drop-shadow-sm tabular-nums">
        {Math.round(score)}
      </span>
    </div>
  )
}

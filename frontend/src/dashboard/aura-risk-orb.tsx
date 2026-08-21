import type { CSSProperties } from 'react'
import { BAND_CHART_COLOR } from './band-colors'
import type { Band } from './types'

interface AuraRiskOrbProps {
  band: Band
}

// "AURA" — the glossy, glowing risk indicator in the first column
// (base/aura.png). Color is the orb's only score-derived signal, via the
// same band-keyed palette score-block.tsx's trend chart already uses
// (band-colors.ts, research.md Decision 6) — no new color thresholds, no
// continuous score->hue interpolation (spec.md Assumptions). The numeric
// score itself renders elsewhere (ScoreBlock), never on the orb. The slow
// pulse below is uniform across bands — it signals "alive", not urgency
// (specs/020-aura-orb-heartbeat/research.md Decisions 1-3).
export function AuraRiskOrb({ band }: AuraRiskOrbProps) {
  const color = BAND_CHART_COLOR[band]

  return (
    <div
      data-testid="aura-risk-orb"
      aria-hidden="true"
      className="relative flex aspect-square w-1/2 items-center justify-center motion-safe:animate-aura-pulse"
      style={{ '--orb-color': color } as CSSProperties}
    >
      {/* Soft ambient halo bleeding past the sphere's edge */}
      <div
        className="absolute inset-[-20%] rounded-full blur-2xl"
        style={{ opacity: 0.35 }}
      />

      {/* The glossy sphere */}
      <div
        className="relative h-[80%] w-[80%] rounded-full"
        style={{
          background: `radial-gradient(circle at 38% 32%, color-mix(in srgb, var(--orb-color) 30%, white), var(--orb-color) 58%, color-mix(in srgb, var(--orb-color) 65%, black) 100%)`,
          boxShadow: `0 0 40px -6px var(--orb-color)`,
        }}
      >
        {/* Specular highlight */}
        <div
          className="absolute top-[16%] left-[20%] h-[34%] w-[34%] rounded-full blur-md"
          style={{ background: 'color-mix(in srgb, white 85%, var(--orb-color))', opacity: 0.6 }}
        />
      </div>
    </div>
  )
}

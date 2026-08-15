import { useEffect, useState } from 'react'
import type { Band } from './types'

interface ScoreBlockProps {
  score: number
  band: Band
  trend: number[]
  onClick: () => void
}

// REQ-M8-10: red only once a promise is broken or a sponsor disengages — the
// band pill itself never turns red on drift alone (that's amber, "watch").
const BAND_STYLES: Record<Band, string> = {
  healthy: 'bg-neutral-100 text-neutral-700',
  watch: 'bg-amber-100 text-amber-800',
  at_risk: 'bg-red-100 text-red-800',
}

const ANIMATION_MS = 800

export function ScoreBlock({ score, band, trend, onClick }: ScoreBlockProps) {
  const previous = trend.length >= 2 ? trend[trend.length - 2] : score
  const [displayed, setDisplayed] = useState(previous)

  useEffect(() => {
    const start = performance.now()
    let frame: number
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / ANIMATION_MS)
      setDisplayed(previous + (score - previous) * t)
      if (t < 1) frame = requestAnimationFrame(tick)
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
    // Re-animate only when the real score changes, not on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [score])

  return (
    <button type="button" onClick={onClick} className="text-left" aria-label="Score detail">
      <div className="flex items-baseline gap-3">
        <span className="text-4xl font-medium tabular-nums text-neutral-900">
          {displayed.toFixed(1)}
        </span>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${BAND_STYLES[band]}`}>
          {band.replace('_', ' ')}
        </span>
      </div>
      {trend.length > 1 && <Sparkline trend={trend} />}
    </button>
  )
}

// SVG-based only (constitution's Technology and Data Standards) — no chart
// library, and not one of REQ-M8-09's forbidden chart types.
function Sparkline({ trend }: { trend: number[] }) {
  const min = Math.min(...trend)
  const max = Math.max(...trend)
  const range = max - min || 1
  const points = trend
    .map((value, index) => {
      const x = (index / (trend.length - 1)) * 118 + 1
      const y = 22 - ((value - min) / range) * 20
      return `${x},${y}`
    })
    .join(' ')

  return (
    <svg width="120" height="24" className="mt-2 text-neutral-400" aria-hidden="true">
      <polyline fill="none" stroke="currentColor" strokeWidth="1.5" points={points} />
    </svg>
  )
}

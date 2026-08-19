import { useEffect, useState } from 'react'
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BAND_CHART_COLOR } from './band-colors'
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
    <div>
      <button type="button" onClick={onClick} className="text-left" aria-label="Score detail">
        <div className="flex items-baseline gap-3">
          {/* FR-009: large, prominent, band-colored score treatment. */}
          <span
            data-testid="score-value"
            className="text-6xl font-semibold tabular-nums text-neutral-900"
          >
            {displayed.toFixed(1)}
          </span>
          <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${BAND_STYLES[band]}`}>
            {band.replace('_', ' ')}
          </span>
        </div>
      </button>

      {/* Constitution v1.3.0 (Full-Stack Engineering §2, "UI & Styling"):
          charts MUST use Recharts — this replaces the previous hand-rolled
          SVG polyline sparkline. Same `trend` prop, same values, index-based
          x-axis (no timestamps existed before and none are added).
          FR-010 (research.md Decision 7): both axes are labeled and visible
          without hovering — the X axis surfaces the same zero-based sequence
          index already used as the chart's dataKey; the Y axis gets a real,
          %-suffixed tick label instead of being hidden. */}
      {trend.length > 1 ? (
        <div className="mt-3 h-32" data-testid="score-trend-chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={trend.map((value, index) => ({ index, value }))}>
              <XAxis dataKey="index" tick={{ fontSize: 10 }} tickLine={false} />
              <YAxis
                domain={['dataMin', 'dataMax']}
                tick={{ fontSize: 10 }}
                tickFormatter={(value) => `${Number(value).toFixed(0)}%`}
                width={36}
              />
              <Tooltip
                formatter={(value) => (value == null ? '' : Number(value).toFixed(1))}
                labelFormatter={() => ''}
              />
              <Area
                type="monotone"
                dataKey="value"
                stroke={BAND_CHART_COLOR[band]}
                strokeWidth={1.5}
                fill={BAND_CHART_COLOR[band]}
                fillOpacity={0.15}
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : trend.length === 1 ? (
        <p className="mt-3 text-xs text-neutral-400">Not enough history yet</p>
      ) : null}
    </div>
  )
}

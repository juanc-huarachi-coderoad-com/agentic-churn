import { Card, CardHeader, CardTitle } from '../components/ui/card'
import { ContributionBars } from './contribution-bars'
import { ScoreBlock } from './score-block'
import type { Band, ContributionBar } from './types'

interface ChurnRiskOverviewCardProps {
  score: number
  band: Band
  trend: number[]
  bars: ContributionBar[]
  onScoreClick: () => void
  onSelect: (scoreContributionId: string) => void
}

// Same band values ScoreBlock's BAND_STYLES already keys off — a
// presentation-only label, not a new classification (REQ-M8-10 still governs
// when a band is actually 'at_risk', unchanged).
const BAND_HEADER_LABEL: Record<Band, string> = {
  healthy: 'HEALTHY',
  watch: 'WATCH',
  at_risk: 'HIGH RISK',
}

const BAND_HEADER_CLASS: Record<Band, string> = {
  healthy: 'bg-neutral-100 text-neutral-700',
  watch: 'bg-amber-100 text-amber-800',
  at_risk: 'bg-red-100 text-red-800',
}

// "Churn Risk Overview" (base/mockup-mainPage.jpg) — composes the existing
// ScoreBlock (score + band + trend) and ContributionBars ("Top risk
// drivers") into one card. Same props flow through unchanged; this
// component only lays them out together.
export function ChurnRiskOverviewCard({
  score,
  band,
  trend,
  bars,
  onScoreClick,
  onSelect,
}: ChurnRiskOverviewCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Churn Risk Overview</CardTitle>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${BAND_HEADER_CLASS[band]}`}>
          {BAND_HEADER_LABEL[band]}
        </span>
      </CardHeader>

      <div className="mt-4">
        <ScoreBlock score={score} band={band} trend={trend} onClick={onScoreClick} />
      </div>

      {bars.length > 0 && (
        <div className="mt-6 border-t border-neutral-100 pt-4">
          <p className="text-xs tracking-wide text-neutral-400 uppercase">Top risk drivers</p>
          <ContributionBars bars={bars} onSelect={onSelect} />
        </div>
      )}
    </Card>
  )
}

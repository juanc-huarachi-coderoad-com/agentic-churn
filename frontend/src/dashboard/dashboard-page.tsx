import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { apiFetch } from '../auth/api-client'
import { EvidencePanel } from '../evidence/evidence-panel'
import { ContributionBars } from './contribution-bars'
import { CoverageLine } from './coverage-line'
import { PulseTimeline } from './pulse-timeline'
import { ScoreBlock } from './score-block'
import { StakeholderCards } from './stakeholder-cards'
import type { DashboardResponse } from './types'

async function fetchDashboard(): Promise<DashboardResponse> {
  const response = await apiFetch('/api/dashboard')
  if (!response.ok) {
    throw new Error(`Dashboard request failed: ${response.status}`)
  }
  return (await response.json()) as DashboardResponse
}

export function DashboardPage() {
  const [selectedContributionId, setSelectedContributionId] = useState<string | null>(null)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboard,
  })

  if (isLoading) {
    return <p className="p-8 text-sm text-neutral-500">Loading…</p>
  }

  if (isError || !data) {
    return <p className="p-8 text-sm text-red-600">Couldn't load the dashboard — try again.</p>
  }

  if (data.state === 'no_profile') {
    return (
      <main className="p-8">
        <p className="text-sm text-neutral-500">No client profile configured.</p>
      </main>
    )
  }

  if (data.state === 'healthy_quiet') {
    // REQ-M8-05: this near-empty screen replaces the normal component set
    // entirely — a healthy account is a near-empty screen, not a subdued
    // version of the full one (constitution P6).
    return (
      <main className="p-8">
        <h1 className="text-lg font-medium text-neutral-900">
          {data.client_header?.client_name}
        </h1>
        <p className="mt-6 text-sm text-neutral-500">{data.message}</p>
      </main>
    )
  }

  // The score itself opens evidence for its single largest contributor — a
  // reasonable "why is the score what it is" entry point (base/...md's "every
  // number is a door"); the number itself doesn't map to one finding.
  const topContributionId =
    data.contribution_bars.length > 0
      ? [...data.contribution_bars].sort((a, b) => Math.abs(b.points) - Math.abs(a.points))[0]
          .score_contribution_id
      : null

  return (
    <main className="p-8">
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-medium text-neutral-900">
          {data.client_header?.client_name}
        </h1>
        {data.client_header?.days_to_renewal != null && (
          <p className="text-xs text-neutral-400">
            {data.client_header.days_to_renewal} days to renewal
          </p>
        )}
      </div>

      {data.message && (
        <p className="mt-4 rounded-md bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
          {data.message}
        </p>
      )}

      {data.score_block && (
        <div className="mt-6">
          <ScoreBlock
            score={data.score_block.score}
            band={data.score_block.band}
            trend={data.score_block.trend}
            onClick={() => topContributionId && setSelectedContributionId(topContributionId)}
          />
        </div>
      )}

      <ContributionBars bars={data.contribution_bars} onSelect={setSelectedContributionId} />
      <PulseTimeline events={data.pulse_timeline} onSelect={setSelectedContributionId} />
      <StakeholderCards cards={data.stakeholder_cards} />
      {data.coverage_line && <CoverageLine coverage={data.coverage_line} />}

      <EvidencePanel
        scoreContributionId={selectedContributionId}
        onClose={() => setSelectedContributionId(null)}
      />
    </main>
  )
}

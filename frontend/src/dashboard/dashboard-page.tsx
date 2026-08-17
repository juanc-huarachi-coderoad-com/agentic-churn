import { useQuery } from '@tanstack/react-query'
import { Bell, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { apiFetch } from '../auth/api-client'
import { AskBar } from '../ask/ask-bar'
import { Icon } from '../components/ui/icon'
import { DraftComposerPanel } from '../draft-composer/draft-composer-panel'
import { EvidencePanel } from '../evidence/evidence-panel'
import { ActionDraftHub } from './action-draft-hub'
import { ChurnRiskOverviewCard } from './churn-risk-overview-card'
import { CoverageLine } from './coverage-line'
import { NarratorPanel } from './narrator-panel'
import { PulseTimeline } from './pulse-timeline'
import { Sidebar } from '../nav/sidebar'
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
  const [draftHandoff, setDraftHandoff] = useState<{
    issueId: string
    stakeholderId: string
  } | null>(null)
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
        <h1 className="text-lg font-medium text-neutral-900">{data.client_header?.client_name}</h1>
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
    <div className="flex min-h-screen bg-neutral-50">
      <Sidebar />

      <main className="min-w-0 flex-1 p-8">
        <div className="flex items-baseline justify-between gap-4">
          <div>
            <h1 className="text-lg font-medium text-neutral-900">
              {data.client_header?.client_name}
            </h1>
            {data.client_header?.days_to_renewal != null && (
              <p className="text-xs text-neutral-400">
                {data.client_header.days_to_renewal} days to renewal
              </p>
            )}
          </div>

          {/* FR-013 (Clarifications 2026-08-17): decorative only — no new
              state, no new API call. Neither the date range nor the
              notification count is backed by real data today. */}
          <div className="flex shrink-0 items-center gap-3">
            <span className="flex items-center gap-1 rounded-md border border-neutral-200 px-3 py-1.5 text-xs text-neutral-600">
              Last 30 days
              <Icon icon={ChevronDown} size={14} />
            </span>
            <span className="flex items-center gap-1.5 rounded-full border border-neutral-200 px-3 py-1.5 text-xs text-neutral-600">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500" aria-hidden="true" />
              Live
            </span>
            <span className="relative flex h-9 w-9 items-center justify-center rounded-md border border-neutral-200 text-neutral-500">
              <Icon icon={Bell} size={16} />
            </span>
          </div>
        </div>

        {data.message && (
          <p className="mt-4 rounded-md bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
            {data.message}
          </p>
        )}

        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_380px]">
          <section aria-label="The Signal Stream" className="min-w-0">
            <h2 className="text-base font-medium text-neutral-900">The Signal Stream</h2>
            <div className="mt-4">
              <PulseTimeline events={data.pulse_timeline} onSelect={setSelectedContributionId} />
            </div>

            {data.narrator && (
              <div className="mt-6">
                <NarratorPanel narrator={data.narrator} />
              </div>
            )}

            {data.stakeholder_cards.length > 0 && (
              <div className="mt-6">
                <StakeholderCards cards={data.stakeholder_cards} />
              </div>
            )}
            {data.coverage_line && <CoverageLine coverage={data.coverage_line} />}
          </section>

          <aside className="flex min-w-0 flex-col gap-6">
            {data.score_block && (
              <ChurnRiskOverviewCard
                score={data.score_block.score}
                band={data.score_block.band}
                trend={data.score_block.trend}
                bars={data.contribution_bars}
                onScoreClick={() =>
                  topContributionId && setSelectedContributionId(topContributionId)
                }
                onSelect={setSelectedContributionId}
              />
            )}
            <ActionDraftHub bars={data.contribution_bars} onSelect={setSelectedContributionId} />
          </aside>
        </div>

        <EvidencePanel
          scoreContributionId={selectedContributionId}
          onClose={() => setSelectedContributionId(null)}
        />
        <DraftComposerPanel
          issueId={draftHandoff?.issueId ?? null}
          stakeholderId={draftHandoff?.stakeholderId ?? null}
          onClose={() => setDraftHandoff(null)}
        />
        <AskBar
          onOpenDraftComposer={(issueId, stakeholderId) =>
            setDraftHandoff({ issueId, stakeholderId })
          }
          onOpenEvidence={setSelectedContributionId}
        />
      </main>
    </div>
  )
}

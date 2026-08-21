import { useQuery } from '@tanstack/react-query'
import { Bell, ChevronDown } from 'lucide-react'
import { useState } from 'react'
import { apiFetch } from '../auth/api-client'
import { AskBar } from '../ask/ask-bar'
import { Icon } from '../components/ui/icon'
import { DraftComposerPanel } from '../draft-composer/draft-composer-panel'
import { EvidencePanel } from '../evidence/evidence-panel'
import { AppShell } from '../nav/app-shell'
import { ActionDraftHub } from './action-draft-hub'
import { AuraRiskOrb } from './aura-risk-orb'
import { ChurnRiskOverviewCard } from './churn-risk-overview-card'
import { CoverageLine } from './coverage-line'
import { NarratorPanel } from './narrator-panel'
import { PulseTimeline } from './pulse-timeline'
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
    scoreContributionId: string
    stakeholderId: string
  } | null>(null)
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard'],
    queryFn: fetchDashboard,
  })

  // research.md Decision 3, data-model.md's "Modal state": Evidence and
  // Draft Composer are mutually exclusive once both are centered dialogs —
  // opening one clears the other's state first, so at most one Dialog is
  // ever open (FR-014).
  function openEvidence(scoreContributionId: string) {
    setDraftHandoff(null)
    setSelectedContributionId(scoreContributionId)
  }

  function openDraftComposer(scoreContributionId: string, stakeholderId: string) {
    setSelectedContributionId(null)
    setDraftHandoff({ scoreContributionId, stakeholderId })
  }

  if (isLoading) {
    return (
      <AppShell>
        <p className="text-sm text-neutral-500">Loading…</p>
      </AppShell>
    )
  }

  if (isError || !data) {
    return (
      <AppShell>
        <p className="text-sm text-red-600">Couldn't load the dashboard — try again.</p>
      </AppShell>
    )
  }

  if (data.state === 'no_profile') {
    return (
      <AppShell>
        <p className="text-sm text-neutral-500">No client profile configured.</p>
      </AppShell>
    )
  }

  if (data.state === 'healthy_quiet') {
    // REQ-M8-05: this near-empty screen replaces the normal component set
    // entirely — a healthy account is a near-empty screen, not a subdued
    // version of the full one (constitution P6).
    return (
      <AppShell>
        <h1 className="text-lg font-medium text-neutral-900">{data.client_header?.client_name}</h1>
        <p className="mt-6 text-sm text-neutral-500">{data.message}</p>
      </AppShell>
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
    <AppShell>
      {/* FR-013 (Clarifications 2026-08-17): decorative only — no new
          state, no new API call. Neither the date range nor the
          notification count is backed by real data today. Company title/
          renewal moved into column 1 (research.md Decision 5). */}
      <div className="flex shrink-0 items-center justify-end gap-3">
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

      {data.message && (
        <p className="mt-4 shrink-0 rounded-md bg-neutral-50 px-3 py-2 text-sm text-neutral-700">
          {data.message}
        </p>
      )}

      <div className="mt-8 grid min-h-0 flex-1 grid-cols-1 gap-6 lg:grid-cols-[320px_minmax(0,1fr)_420px] lg:overflow-hidden">
        {/* Column 1 — company/AURA/Assistant (FR-003, FR-004). */}
        <section
          aria-label="Company and AURA Assistant"
          data-testid="dashboard-column-1"
          className="flex min-w-0 flex-col gap-6 lg:h-full lg:overflow-y-auto"
        >
          <div className="text-center">
            <h1 className="text-lg font-medium text-neutral-900">
              {data.client_header?.client_name}
            </h1>
            {data.client_header?.days_to_renewal != null && (
              <p className="text-xs text-neutral-400">
                {data.client_header.days_to_renewal} days to renewal
              </p>
            )}
          </div>

          <div className="flex justify-center">
            {data.score_block && <AuraRiskOrb band={data.score_block.band} />}
          </div>
          <AskBar onOpenDraftComposer={openDraftComposer} onOpenEvidence={openEvidence} />
        </section>

        {/* Column 2 — The Signal Stream, then Narrator/Stakeholders/
              Coverage, unchanged in function, relocated only (FR-005,
              FR-019, research.md Decision 4). */}
        <section
          aria-label="The Signal Stream"
          data-testid="dashboard-column-2"
          className="min-w-0 lg:h-full lg:overflow-y-auto"
        >
          <h2 className="text-base font-medium text-neutral-900">The Signal Stream</h2>
          <div className="mt-4">
            <PulseTimeline events={data.pulse_timeline} onSelect={openEvidence} />
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

        {/* Column 3 — Churn Risk Overview + Action & Draft Hub
              (FR-009, FR-010, FR-011). */}
        <aside
          aria-label="Churn Risk Overview and Action Hub"
          data-testid="dashboard-column-3"
          className="flex min-w-0 flex-col gap-6 lg:h-full lg:overflow-y-auto"
        >
          {data.score_block && (
            <ChurnRiskOverviewCard
              score={data.score_block.score}
              band={data.score_block.band}
              trend={data.score_block.trend}
              bars={data.contribution_bars}
              onScoreClick={() => topContributionId && openEvidence(topContributionId)}
              onSelect={openEvidence}
            />
          )}
          <ActionDraftHub bars={data.contribution_bars} onSelect={openEvidence} />
        </aside>
      </div>

      <EvidencePanel
        scoreContributionId={selectedContributionId}
        onClose={() => setSelectedContributionId(null)}
      />
      <DraftComposerPanel
        scoreContributionId={draftHandoff?.scoreContributionId ?? null}
        stakeholderId={draftHandoff?.stakeholderId ?? null}
        onClose={() => setDraftHandoff(null)}
      />
    </AppShell>
  )
}

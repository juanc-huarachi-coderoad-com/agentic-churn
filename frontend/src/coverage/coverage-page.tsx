import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../auth/api-client'
import { AppShell } from '../nav/app-shell'
import { MeetingConsentPanel } from './meeting-consent-panel'
import type { CoverageResponse } from './types'
import { useRefreshMeetingAudio } from './use-meeting-audio-refresh'

async function fetchCoverage(): Promise<CoverageResponse> {
  const response = await apiFetch('/api/coverage')
  if (!response.ok) {
    throw new Error(`Coverage request failed: ${response.status}`)
  }
  return (await response.json()) as CoverageResponse
}

const STATUS_LABEL: Record<string, string> = {
  connected: 'Connected',
  degraded: 'Degraded',
  disconnected: 'Disconnected',
}

// A degraded source must look visibly different, not just differently
// worded (constitution P5, "admit what we cannot see") — color alone would
// violate P11's accessibility rule, so the label text itself already
// differs ("Degraded" vs "Connected") and this only adds emphasis.
const STATUS_CLASS: Record<string, string> = {
  connected: 'text-neutral-500',
  degraded: 'font-medium text-red-600',
  disconnected: 'font-medium text-red-600',
}

// The dedicated system health screen (base/...md §11.2's screen inventory) —
// distinct from the dashboard's own one-line coverage summary.
export function CoveragePage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['coverage'],
    queryFn: fetchCoverage,
  })
  const refresh = useRefreshMeetingAudio()

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
        <p className="text-sm text-red-600">Couldn't load system health — try again.</p>
      </AppShell>
    )
  }

  return (
    <AppShell>
      <div className="lg:h-full lg:overflow-y-auto">
        <div className="flex items-center justify-between">
          <h1 className="text-lg font-medium text-neutral-900">System health</h1>
          <button
            type="button"
            onClick={() => refresh.mutate()}
            disabled={refresh.isPending}
            className="rounded border border-neutral-300 px-3 py-1.5 text-sm text-neutral-700 disabled:opacity-50"
          >
            {refresh.isPending ? 'Checking…' : 'Check for new meeting audio'}
          </button>
        </div>

        {refresh.isSuccess && (
          <p className="mt-2 text-sm text-neutral-500">
            {refresh.data.source_error
              ? `Couldn't check — ${refresh.data.source_error}`
              : refresh.data.recordings_found === 0
                ? 'Nothing new since the last check.'
                : `Found ${refresh.data.recordings_found}, transcribed ${refresh.data.transcribed}.`}
          </p>
        )}
        {refresh.isError && (
          <p className="mt-2 text-sm text-red-600">Couldn't check for new audio — try again.</p>
        )}

        <ul className="mt-6 space-y-2">
          {data.sources.map((source) => (
            <li
              key={source.source_type}
              className="flex items-center justify-between border-b border-neutral-100 pb-2 text-sm"
            >
              <span className="text-neutral-800 capitalize">{source.source_type}</span>
              <span className={STATUS_CLASS[source.status] ?? 'text-neutral-500'}>
                {STATUS_LABEL[source.status] ?? source.status}
              </span>
              <span className="text-xs text-neutral-400">
                {source.last_successful_sync_at
                  ? new Date(source.last_successful_sync_at).toLocaleString()
                  : 'never synced'}
              </span>
            </li>
          ))}
        </ul>

        <h2 className="mt-8 text-sm font-medium text-neutral-900">Quarantine</h2>
        {data.quarantine.length === 0 ? (
          <p className="mt-2 text-sm text-neutral-500">Nothing quarantined.</p>
        ) : (
          <ul className="mt-2 space-y-1 text-sm text-neutral-700">
            {data.quarantine.map((entry) => (
              <li key={entry.finding_id}>{entry.failed_check}</li>
            ))}
          </ul>
        )}

        <MeetingConsentPanel />
      </div>
    </AppShell>
  )
}

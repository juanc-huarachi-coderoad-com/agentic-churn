import { useQuery } from '@tanstack/react-query'
import { apiFetch } from '../auth/api-client'

// Mirrors contracts/dashboard.md's shell-scoped response — score_block/
// contribution_bars/pulse_timeline/stakeholder_cards/coverage_line are absent, not
// optional, until feature 006 extends this contract.
interface DashboardShellResponse {
  client_header: { client_name: string } | null
  state: 'learning' | 'no_profile'
  learning_message: string | null
}

async function fetchDashboard(): Promise<DashboardShellResponse> {
  const response = await apiFetch('/api/dashboard')
  if (!response.ok) {
    throw new Error(`Dashboard request failed: ${response.status}`)
  }
  return (await response.json()) as DashboardShellResponse
}

export function DashboardPage() {
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

  return (
    <main className="p-8">
      <h1 className="text-lg font-medium text-neutral-900">{data.client_header?.client_name}</h1>
      <p className="mt-2 text-sm text-neutral-500">{data.learning_message}</p>
    </main>
  )
}

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from '../auth/api-client'
import { DashboardPage } from './dashboard-page'
import type { DashboardResponse } from './types'

vi.mock('../auth/api-client', () => ({
  apiFetch: vi.fn(),
}))

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 })
}

function renderDashboard() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter initialEntries={['/dashboard']}>
      <QueryClientProvider client={queryClient}>
        <DashboardPage />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

const BASE_RESPONSE: DashboardResponse = {
  client_header: { client_name: 'Meridian Logistics', band: 'at_risk', days_to_renewal: 85 },
  state: 'normal',
  message: null,
  score_block: { score: 85.6, band: 'at_risk', trend: [80.0, 85.6] },
  contribution_bars: [
    {
      score_contribution_id: 'a23cd997-11bb-4872-905b-5337e9b2bd0e',
      label: 'broken_response_promise',
      points: 39.0,
      is_positive: false,
    },
  ],
  pulse_timeline: [
    {
      event_id: '45765fc1-57e9-444b-b73d-1cfbd1e0ea70',
      occurred_at: '2026-08-10T12:40:00Z',
      severity: 'at_risk',
      quoted_text: 'Slow API response',
      score_contribution_id: 'a23cd997-11bb-4872-905b-5337e9b2bd0e',
    },
  ],
  stakeholder_cards: [
    {
      stakeholder_id: '21000000-0000-0000-0000-000000000001',
      name: 'Ana Reyes',
      role: 'CTO',
      tone_trajectory: 'unknown',
      last_seen_at: '2026-08-13T14:14:00Z',
      status: 'active',
    },
  ],
  coverage_line: { sources_read: 3, sources_expected: 3, complete_to: null, status: 'ok' },
  narrator: null,
}

describe('DashboardPage', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
  })

  it('renders the real score, contribution bar, and pulse event for the normal state', async () => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse(BASE_RESPONSE))
    renderDashboard()

    expect(await screen.findByText('Meridian Logistics')).toBeInTheDocument()
    expect(screen.getByText('85 days to renewal')).toBeInTheDocument()
    // The same contribution bar now renders in both the Churn Risk Overview
    // card's "Top risk drivers" and the Action & Draft Hub's ranked list —
    // two visualizations of the same data, per the mockup.
    expect(screen.getAllByText('broken response promise').length).toBeGreaterThan(0)
    expect(screen.getByText('“Slow API response”')).toBeInTheDocument()
    expect(screen.getByText('Ana Reyes')).toBeInTheDocument()
  })

  it('renders the near-empty screen for healthy_quiet, not the full component set', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        ...BASE_RESPONSE,
        state: 'healthy_quiet',
        message: 'Nothing needs you today. Last checked 4 minutes ago.',
        score_block: null,
        contribution_bars: [],
        pulse_timeline: [],
      }),
    )
    renderDashboard()

    expect(
      await screen.findByText('Nothing needs you today. Last checked 4 minutes ago.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('broken response promise')).not.toBeInTheDocument()
  })

  it('renders the no_profile state honestly, with no fabricated client name', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({ client_header: null, state: 'no_profile', message: null }),
    )
    renderDashboard()

    expect(await screen.findByText('No client profile configured.')).toBeInTheDocument()
  })

  it('renders a state banner message above the normal component set', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        ...BASE_RESPONSE,
        state: 'source_down',
        message: "Email hasn't been read since Tue 09:14 — reconnect.",
      }),
    )
    renderDashboard()

    expect(
      await screen.findByText("Email hasn't been read since Tue 09:14 — reconnect."),
    ).toBeInTheDocument()
    // The rest of the real component set still renders alongside the banner.
    expect(screen.getAllByText('broken response promise').length).toBeGreaterThan(0)
  })

  it.each([
    ['catching_up', 'Partial data — 40 minutes behind.'],
    [
      'unresolved_person',
      "Someone at meridian.com has written 3 times and isn't in the profile. Who is this?",
    ],
    ['learning', 'Still learning — 3 of 6 signal types available.'],
  ])('renders the %s state banner with its exact required copy', async (state, message) => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse({ ...BASE_RESPONSE, state, message }))
    renderDashboard()

    expect(await screen.findByText(message)).toBeInTheDocument()
  })

  it('opens the evidence panel when a contribution bar is clicked', async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path.startsWith('/api/evidence/')) {
        return Promise.resolve(
          jsonResponse({
            finding_id: 'f1',
            finding_type: 'broken_response_promise',
            points: 39.0,
            baseline_value: 'responds within 4 promised business hours',
            current_value: '50 business hours elapsed, still open',
            what_changed: [],
            quoted_messages: [],
            arithmetic_explanation: 'Base 20 points — 39.0 points total.',
          }),
        )
      }
      return Promise.resolve(jsonResponse(BASE_RESPONSE))
    })
    renderDashboard()

    const [bar] = await screen.findAllByText('broken response promise')
    await userEvent.click(bar)

    await waitFor(() => {
      expect(screen.getByText('responds within 4 promised business hours')).toBeInTheDocument()
    })
  })
})

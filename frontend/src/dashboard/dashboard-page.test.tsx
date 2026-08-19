import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
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
      event_type: 'ticket_state_change',
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

  it('renders three independently-scrollable columns (FR-001, FR-002, FR-003, FR-019)', async () => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse(BASE_RESPONSE))
    renderDashboard()

    await screen.findByText('Meridian Logistics')

    const column1 = screen.getByTestId('dashboard-column-1')
    const column2 = screen.getByTestId('dashboard-column-2')
    const column3 = screen.getByTestId('dashboard-column-3')

    // Company title/renewal and the AURA orb live in column 1, not the old
    // top header row (research.md Decision 5).
    expect(column1).toHaveTextContent('Meridian Logistics')
    expect(column1).toHaveTextContent('85 days to renewal')
    expect(within(column1).getByTestId('aura-risk-orb')).toBeInTheDocument()

    // Signal Stream, then Stakeholders and Coverage, all reachable by
    // scrolling column 2 (FR-019) — nothing relocated to another column.
    expect(column2).toHaveTextContent('Slow API response')
    expect(column2).toHaveTextContent('Ana Reyes')

    // Churn Risk Overview and the Action & Draft Hub stay in column 3.
    expect(column3).toHaveTextContent('Churn Risk Overview')
    expect(column3).toHaveTextContent('The Action & Draft Hub')

    // Each column is independently scrollable within a bounded height —
    // the page itself never scrolls as a whole (FR-002).
    for (const column of [column1, column2, column3]) {
      expect(column.className).toMatch(/overflow-y-auto/)
    }
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

  it('closes Evidence before opening Draft Composer, and vice versa — at most one modal at a time (FR-014, research.md Decision 3)', async () => {
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
      if (path === '/api/ask') {
        return Promise.resolve(
          jsonResponse({
            intent: 'draft_outreach',
            parts: [
              {
                type: 'component',
                component: 'draft_handoff',
                component_props: { issue_id: 'iss-A', stakeholder_id: 'stk-ana' },
              },
            ],
          }),
        )
      }
      if (path === '/api/drafts') {
        return Promise.resolve(
          jsonResponse({
            id: 'draft-1',
            draft_text: 'Draft body',
            tone_variant: 'direct',
            evidence_event_ids: [],
            checks_passed: true,
          }),
        )
      }
      return Promise.resolve(jsonResponse(BASE_RESPONSE))
    })
    renderDashboard()
    await screen.findByText('Meridian Logistics')

    // Ask the docked assistant a question whose answer offers to open the
    // Draft Composer, before Evidence is open — the assistant panel isn't
    // blocked yet at this point.
    await userEvent.type(screen.getByLabelText('Ask a question'), 'draft outreach to Ana')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))
    const openDraftComposerButton = await screen.findByRole('button', {
      name: /open the draft composer/i,
    })

    // Open Evidence from a contribution bar. A real, accessible modal
    // (Radix's own inert-background behavior) now blocks pointer
    // interaction with anything outside it — exactly what FR-016 asks for —
    // so the "select a different item while a modal is open" scenario is
    // exercised here via `fireEvent` (bypassing that same-tick pointer-
    // events guard) to assert the application's own mutual-exclusion state
    // logic (research.md Decision 3), independent of Radix's own inertness.
    const [bar] = await screen.findAllByText('broken response promise')
    await userEvent.click(bar)
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: 'Evidence trace' })).toBeInTheDocument()
    })

    fireEvent.click(openDraftComposerButton)

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Evidence trace' })).not.toBeInTheDocument()
    })
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: 'Draft composer' })).toBeInTheDocument()
    })
    expect(screen.getAllByRole('dialog')).toHaveLength(1)
    // Belt-and-suspenders against Radix's own `aria-hide`-the-others
    // behavior masking a still-mounted second dialog from the accessibility
    // tree: assert only one [role="dialog"] node exists in the DOM at all,
    // not just in the (aria-hidden-filtered) accessible query results —
    // this is what actually proves *our* mutual-exclusion state logic
    // unmounted Evidence, not Radix incidentally hiding it.
    expect(document.querySelectorAll('[role="dialog"]')).toHaveLength(1)
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

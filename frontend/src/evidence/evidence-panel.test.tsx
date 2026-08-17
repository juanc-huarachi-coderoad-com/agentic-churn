import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from '../auth/api-client'
import { EvidencePanel } from './evidence-panel'

vi.mock('../auth/api-client', () => ({
  apiFetch: vi.fn(),
}))

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 })
}

function renderPanel(scoreContributionId: string | null, onClose = vi.fn()) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <EvidencePanel scoreContributionId={scoreContributionId} onClose={onClose} />
    </QueryClientProvider>,
  )
}

const WORKED_EXAMPLE = {
  finding_id: 'ba87c77f-e21f-45af-9705-533138e948bf',
  finding_type: 'broken_response_promise',
  points: 39.0,
  baseline_value: 'responds within 4 promised business hours',
  current_value: '50 business hours elapsed, still open',
  what_changed: [
    'response time exceeded the promised threshold',
    'the ticket has not yet resolved',
  ],
  quoted_messages: [
    { event_id: '45765fc1-...', text: 'Slow API response', occurred_at: '2026-08-10T12:40:00Z' },
  ],
  arithmetic_explanation:
    'Base 20 points for broken_response_promise, increased 50% for product area criticality, increased 30% for recency — 39.0 points total.',
  disclosure_text: null,
}

describe('EvidencePanel', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
  })

  it('renders nothing when no contribution is selected', () => {
    const { container } = renderPanel(null)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders the worked example: comparison, what-changed, quotes, arithmetic', async () => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse(WORKED_EXAMPLE))
    renderPanel('ba87c77f-e21f-45af-9705-533138e948bf')

    expect(await screen.findByText('responds within 4 promised business hours')).toBeInTheDocument()
    expect(screen.getByText('50 business hours elapsed, still open')).toBeInTheDocument()
    expect(screen.getByText('response time exceeded the promised threshold')).toBeInTheDocument()
    expect(screen.getByText('“Slow API response”')).toBeInTheDocument()
    expect(screen.getByText(/39\.0 points total/)).toBeInTheDocument()
    // Verdict controls are always present (FR-001); disclosure text is not,
    // since this pattern has never been damped.
    expect(screen.getByRole('button', { name: 'False alarm' })).toBeInTheDocument()
    expect(screen.queryByText(/weight reduced/i)).not.toBeInTheDocument()
  })

  it('renders the disclosure text when the pattern is damped', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        ...WORKED_EXAMPLE,
        disclosure_text: 'weight reduced — your team flagged this pattern as a false alarm',
      }),
    )
    renderPanel('ba87c77f-e21f-45af-9705-533138e948bf')

    expect(
      await screen.findByText('weight reduced — your team flagged this pattern as a false alarm'),
    ).toBeInTheDocument()
  })

  it('submits a verdict in a single click, with no modal or confirmation', async () => {
    vi.mocked(apiFetch).mockImplementation(async (path) => {
      if (path === '/api/feedback') {
        return new Response(null, { status: 204 })
      }
      return jsonResponse(WORKED_EXAMPLE)
    })
    renderPanel('ba87c77f-e21f-45af-9705-533138e948bf')

    await screen.findByText('responds within 4 promised business hours')
    await userEvent.click(screen.getByRole('button', { name: 'False alarm' }))

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/feedback',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ finding_id: WORKED_EXAMPLE.finding_id, verdict: 'false_alarm' }),
      }),
    )
    // No modal/dialog rendered as a result of the click.
    expect(screen.queryByRole('dialog', { name: /confirm/i })).not.toBeInTheDocument()
  })

  it('calls onClose when the close button is clicked', async () => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse(WORKED_EXAMPLE))
    const onClose = vi.fn()
    renderPanel('ba87c77f-e21f-45af-9705-533138e948bf', onClose)

    await screen.findByText('responds within 4 promised business hours')
    await userEvent.click(screen.getByText('Close'))

    expect(onClose).toHaveBeenCalled()
  })

  it('renders the honest fallback for a finding type outside the dispatch table', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        ...WORKED_EXAMPLE,
        finding_type: 'escalation_language',
        baseline_value:
          "a detailed comparison for this finding type isn't available until its owning reader ships",
        current_value:
          "a detailed comparison for this finding type isn't available until its owning reader ships",
        what_changed: [],
      }),
    )
    renderPanel('a23cd997-11bb-4872-905b-5337e9b2bd0e')

    expect(await screen.findAllByText(/isn't available/)).toHaveLength(2)
  })
})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from '../auth/api-client'
import { AskBar } from './ask-bar'

vi.mock('../auth/api-client', () => ({
  apiFetch: vi.fn(),
}))

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 })
}

function renderAskBar() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <AskBar />
    </QueryClientProvider>,
  )
}

describe('AskBar', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
  })

  it('renders already expanded on mount — ready to accept a message, no launcher button (FR-004, SC-007)', () => {
    renderAskBar()

    expect(screen.getByLabelText('Ask a question')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Open assistant' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Collapse assistant' })).not.toBeInTheDocument()
    expect(screen.getByTestId('ask-bar').dataset.state).toBe('idle')
  })

  it('starts idle, transitions through thinking, and renders the matched component', async () => {
    let resolveFetch!: (response: Response) => void
    vi.mocked(apiFetch).mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve
      }),
    )
    renderAskBar()

    expect(screen.getByTestId('ask-bar').dataset.state).toBe('idle')

    await userEvent.type(screen.getByLabelText('Ask a question'), 'why did the score go up?')
    await userEvent.click(screen.getByRole('button', { name: /ask|thinking/i }))

    await waitFor(() => expect(screen.getByTestId('ask-bar').dataset.state).toBe('thinking'))
    expect(screen.getByRole('button', { name: 'Thinking…' })).toBeDisabled()

    resolveFetch(
      jsonResponse({
        intent: 'score_delta',
        parts: [
          {
            type: 'component',
            component: 'delta_breakdown',
            component_props: { score: 61.0, band: 'at_risk', causes: [] },
          },
        ],
      }),
    )

    await waitFor(() => expect(screen.getByTestId('ask-bar').dataset.state).toBe('answered'))
    expect(screen.getByText(/Score 61/)).toBeInTheDocument()
  })

  it('renders a fallback answer, clearly marked as such', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        fallback_text: "I describe today's evidence — I don't forecast.",
        sources: [],
        declined_reason: 'prediction',
      }),
    )
    renderAskBar()

    await userEvent.type(screen.getByLabelText('Ask a question'), 'will they cancel?')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))

    expect(
      await screen.findByText("I describe today's evidence — I don't forecast."),
    ).toBeInTheDocument()
    expect(screen.getByText('Fallback answer')).toBeInTheDocument()
  })

  it('preserves the last exchange across scrolling/interacting elsewhere (FR-004 Acceptance Scenario 2)', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        fallback_text: "I describe today's evidence — I don't forecast.",
        sources: [],
        declined_reason: 'prediction',
      }),
    )
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { rerender } = render(
      <QueryClientProvider client={queryClient}>
        <AskBar />
      </QueryClientProvider>,
    )

    await userEvent.type(screen.getByLabelText('Ask a question'), 'will they cancel?')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))
    expect(
      await screen.findByText("I describe today's evidence — I don't forecast."),
    ).toBeInTheDocument()

    // Re-rendering the same mounted component (standing in for "scrolling/
    // interacting elsewhere on the dashboard") must never reset or discard
    // the current exchange — no collapse state exists anymore to reset it.
    rerender(
      <QueryClientProvider client={queryClient}>
        <AskBar />
      </QueryClientProvider>,
    )

    expect(screen.getByText("I describe today's evidence — I don't forecast.")).toBeInTheDocument()
  })
})

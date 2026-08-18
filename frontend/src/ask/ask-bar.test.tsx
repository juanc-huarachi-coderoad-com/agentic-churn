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

async function openAssistant() {
  await userEvent.click(screen.getByRole('button', { name: 'Open assistant' }))
}

describe('AskBar', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
  })

  it('starts collapsed on every mount — launcher only, no question input visible', () => {
    renderAskBar()

    expect(screen.getByRole('button', { name: 'Open assistant' })).toBeInTheDocument()
    expect(screen.queryByLabelText('Ask a question')).not.toBeInTheDocument()
    expect(screen.getByTestId('ask-bar').dataset.state).toBe('idle')
  })

  it('opens on demand and can be collapsed again', async () => {
    renderAskBar()

    await openAssistant()
    expect(screen.getByLabelText('Ask a question')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Collapse assistant' }))
    expect(screen.queryByLabelText('Ask a question')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Open assistant' })).toBeInTheDocument()
  })

  it('starts idle, transitions through thinking, and renders the matched component', async () => {
    let resolveFetch!: (response: Response) => void
    vi.mocked(apiFetch).mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve
      }),
    )
    renderAskBar()
    await openAssistant()

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
    await openAssistant()

    await userEvent.type(screen.getByLabelText('Ask a question'), 'will they cancel?')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))

    expect(
      await screen.findByText("I describe today's evidence — I don't forecast."),
    ).toBeInTheDocument()
    expect(screen.getByText('Fallback answer')).toBeInTheDocument()
  })

  it('preserves the last exchange across collapse and reopen (FR-008)', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        fallback_text: "I describe today's evidence — I don't forecast.",
        sources: [],
        declined_reason: 'prediction',
      }),
    )
    renderAskBar()
    await openAssistant()

    await userEvent.type(screen.getByLabelText('Ask a question'), 'will they cancel?')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))
    expect(
      await screen.findByText("I describe today's evidence — I don't forecast."),
    ).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: 'Collapse assistant' }))
    await openAssistant()

    expect(screen.getByText("I describe today's evidence — I don't forecast.")).toBeInTheDocument()
  })
})

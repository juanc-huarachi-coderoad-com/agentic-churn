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

function lastRequestBody(): Record<string, unknown> {
  const calls = vi.mocked(apiFetch).mock.calls
  const init = calls[calls.length - 1]?.[1] as RequestInit
  return JSON.parse(init.body as string) as Record<string, unknown>
}

function renderAskBar() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <AskBar />
    </QueryClientProvider>,
  )
}

async function askAndAwaitAnswer(question: string) {
  await userEvent.type(screen.getByLabelText('Ask a question'), question)
  await userEvent.click(screen.getByRole('button', { name: /ask/i }))
  await waitFor(() => expect(screen.getByText(question)).toBeInTheDocument())
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

  // specs/017-assistant-chat-conversation — User Story 1 (T005/T006)
  it('appends a second question/answer pair below the first instead of replacing it (US1)', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(
        jsonResponse({ fallback_text: 'first answer', sources: [], declined_reason: 'unclear' }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ fallback_text: 'second answer', sources: [], declined_reason: 'unclear' }),
      )
    renderAskBar()

    await askAndAwaitAnswer('first question')
    expect(await screen.findByText('first answer')).toBeInTheDocument()

    await askAndAwaitAnswer('second question')
    expect(await screen.findByText('second answer')).toBeInTheDocument()

    // Both pairs remain simultaneously visible — nothing was discarded.
    expect(screen.getByText('first question')).toBeInTheDocument()
    expect(screen.getByText('first answer')).toBeInTheDocument()
    expect(screen.getByText('second question')).toBeInTheDocument()
    expect(screen.getByText('second answer')).toBeInTheDocument()
    expect(screen.getAllByTestId('turn')).toHaveLength(2)
  })

  it('keeps all 10 consecutive question/answer pairs visible, none lost or overwritten (US1, SC-001)', async () => {
    vi.mocked(apiFetch).mockImplementation(async () =>
      jsonResponse({ fallback_text: 'ack', sources: [], declined_reason: 'unclear' }),
    )
    renderAskBar()

    for (let i = 1; i <= 10; i++) {
      await askAndAwaitAnswer(`question ${i}`)
    }

    for (let i = 1; i <= 10; i++) {
      expect(screen.getByText(`question ${i}`)).toBeInTheDocument()
    }
    expect(screen.getAllByTestId('turn')).toHaveLength(10)
    expect(screen.getAllByText('ack')).toHaveLength(10)
  })

  it('shows an error state for a failed turn without losing prior turns, and allows continuing (US1, FR-013)', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(
        jsonResponse({ fallback_text: 'first answer', sources: [], declined_reason: 'unclear' }),
      )
      .mockRejectedValueOnce(new Error('network down'))
      .mockResolvedValueOnce(
        jsonResponse({ fallback_text: 'third answer', sources: [], declined_reason: 'unclear' }),
      )
    renderAskBar()

    await askAndAwaitAnswer('first question')
    expect(await screen.findByText('first answer')).toBeInTheDocument()

    await userEvent.type(screen.getByLabelText('Ask a question'), 'second question')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))

    expect(
      await screen.findByText(
        "That's taking longer than it should — try again, or check the dashboard directly.",
      ),
    ).toBeInTheDocument()
    // The prior, successfully-answered turn is untouched.
    expect(screen.getByText('first question')).toBeInTheDocument()
    expect(screen.getByText('first answer')).toBeInTheDocument()

    await askAndAwaitAnswer('third question')
    expect(await screen.findByText('third answer')).toBeInTheDocument()
  })

  // specs/017-assistant-chat-conversation — User Story 2 (T010/T011/T012)
  it('clears the input synchronously on submit and shows the sent text as the newest turn (US2)', async () => {
    let resolveFetch!: (response: Response) => void
    vi.mocked(apiFetch).mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve
      }),
    )
    renderAskBar()

    const input = screen.getByLabelText('Ask a question') as HTMLInputElement
    await userEvent.type(input, 'why did the score go up?')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))

    // Synchronous, not just eventual: no leftover text once the click's
    // event handlers have run.
    expect(input.value).toBe('')
    expect(screen.getByText('why did the score go up?')).toBeInTheDocument()

    resolveFetch(
      jsonResponse({ fallback_text: 'done', sources: [], declined_reason: 'unclear' }),
    )
    await screen.findByText('done')
  })

  it('disables sending while a turn is pending, typing stays enabled, and re-enables the instant it resolves (US2, FR-014)', async () => {
    let resolveFetch!: (response: Response) => void
    vi.mocked(apiFetch).mockReturnValue(
      new Promise((resolve) => {
        resolveFetch = resolve
      }),
    )
    renderAskBar()

    await userEvent.type(screen.getByLabelText('Ask a question'), 'first question')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))

    const sendButton = await screen.findByRole('button', { name: 'Thinking…' })
    expect(sendButton).toBeDisabled()

    // Typing itself is never blocked, only sending.
    const input = screen.getByLabelText('Ask a question') as HTMLInputElement
    await userEvent.type(input, 'queued up next')
    expect(input.value).toBe('queued up next')

    resolveFetch(
      jsonResponse({ fallback_text: 'answer', sources: [], declined_reason: 'unclear' }),
    )
    await waitFor(() => expect(screen.getByRole('button', { name: 'Ask' })).not.toBeDisabled())
  })

  it('does not add a turn or clear the input for an empty or whitespace-only submit (US2, FR-006)', async () => {
    renderAskBar()

    const input = screen.getByLabelText('Ask a question') as HTMLInputElement
    await userEvent.type(input, '   ')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))

    expect(input.value).toBe('   ')
    expect(screen.queryAllByTestId('turn')).toHaveLength(0)
    expect(apiFetch).not.toHaveBeenCalled()
  })

  // specs/017-assistant-chat-conversation — User Story 3 (T016)
  it('renders a null-declined_reason reply as plain conversational text, without the "Fallback answer" caption (US3)', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        fallback_text: 'Hi! I can help with things like why the score changed.',
        sources: [],
        declined_reason: null,
      }),
    )
    renderAskBar()

    await userEvent.type(screen.getByLabelText('Ask a question'), 'hi')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))

    expect(
      await screen.findByText('Hi! I can help with things like why the score changed.'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Fallback answer')).not.toBeInTheDocument()
  })

  // specs/017-assistant-chat-conversation — User Story 4 (T022)
  it('sends the prior turn as history on a follow-up question (US4)', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(
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
      .mockResolvedValueOnce(
        jsonResponse({ fallback_text: 'follow-up answer', sources: [], declined_reason: 'unclear' }),
      )
    renderAskBar()

    await askAndAwaitAnswer('why did the score go up?')
    await screen.findByText(/Score 61/)

    await askAndAwaitAnswer('what about last quarter?')

    const body = lastRequestBody()
    expect(body.question).toBe('what about last quarter?')
    expect(body.history).toEqual([
      {
        question: 'why did the score go up?',
        answer: {
          intent: 'score_delta',
          parts: [
            {
              type: 'component',
              component: 'delta_breakdown',
              component_props: { score: 61.0, band: 'at_risk', causes: [] },
            },
          ],
        },
      },
    ])
  })

  // specs/017-assistant-chat-conversation — User Story 5 (T028/T029)
  it('renders two turns with different part shapes correctly and independently (US5)', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(
        jsonResponse({
          intent: 'top_risk',
          parts: [
            {
              type: 'component',
              component: 'ranked_issues',
              component_props: { ranked_issues: [] },
            },
          ],
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          intent: 'score_delta',
          parts: [
            { type: 'text', markdown: 'The score dropped mainly for one reason.' },
            {
              type: 'component',
              component: 'delta_breakdown',
              component_props: { score: 61.0, band: 'at_risk', causes: [] },
            },
          ],
        }),
      )
    renderAskBar()

    await askAndAwaitAnswer('what is the top risk?')
    await askAndAwaitAnswer('why did the score drop?')

    expect(screen.getByText('The score dropped mainly for one reason.')).toBeInTheDocument()
    expect(screen.getByText(/Score 61/)).toBeInTheDocument()
    expect(screen.getAllByTestId('turn')).toHaveLength(2)
  })

  it('renders a plain conversational reply as text only, with no forced/empty visual element (US5)', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        fallback_text: 'Hi! I can help with things like why the score changed.',
        sources: [],
        declined_reason: null,
      }),
    )
    renderAskBar()

    await userEvent.type(screen.getByLabelText('Ask a question'), 'hi')
    await userEvent.click(screen.getByRole('button', { name: /ask/i }))

    await screen.findByText('Hi! I can help with things like why the score changed.')
    expect(screen.queryByRole('list')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /open the draft composer/i })).not.toBeInTheDocument()
  })
})

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from '../auth/api-client'
import { DraftComposerPanel } from './draft-composer-panel'

vi.mock('../auth/api-client', () => ({
  apiFetch: vi.fn(),
}))

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status })
}

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const onClose = vi.fn()
  render(
    <QueryClientProvider client={queryClient}>
      <DraftComposerPanel issueId="iss-A" stakeholderId="stk-ana" onClose={onClose} />
    </QueryClientProvider>,
  )
  return { onClose }
}

describe('DraftComposerPanel', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
    Object.assign(navigator, { clipboard: { writeText: vi.fn().mockResolvedValue(undefined) } })
  })

  it('renders inside the shared Radix Dialog primitive, not the old right-docked panel (FR-013)', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        id: 'draft-1',
        draft_text: 'Ana — we took 19 hours to respond; we promised 4.',
        tone_variant: 'direct',
        evidence_event_ids: ['evt-2'],
        checks_passed: true,
      }),
    )
    renderPanel()

    const dialog = await screen.findByRole('dialog', { name: 'Draft composer' })
    expect(dialog).toBeInTheDocument()
    // The backdrop is components/ui/dialog.tsx's DialogOverlay, not the
    // previous hand-rolled `fixed inset-0 ... flex justify-end` <div>.
    expect(screen.getByTestId('dialog-overlay')).toBeInTheDocument()
  })

  it('generates on mount and switching tone tabs issues a new request', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        id: 'draft-1',
        draft_text: 'Ana — we took 19 hours to respond; we promised 4.',
        tone_variant: 'direct',
        evidence_event_ids: ['evt-2'],
        checks_passed: true,
      }),
    )
    renderPanel()

    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(1))
    expect(await screen.findByText(/we took 19 hours to respond/)).toBeInTheDocument()

    await userEvent.click(screen.getByRole('tab', { name: 'brief' }))

    await waitFor(() => expect(apiFetch).toHaveBeenCalledTimes(2))
    const secondCallBody = JSON.parse(
      vi.mocked(apiFetch).mock.calls[1][1]?.body as string,
    ) as { tone_variant: string }
    expect(secondCallBody.tone_variant).toBe('brief')
  })

  it('never renders an editable text field for the draft', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        id: 'draft-1',
        draft_text: 'Ana — we took 19 hours to respond; we promised 4.',
        tone_variant: 'direct',
        evidence_event_ids: ['evt-2'],
        checks_passed: true,
      }),
    )
    renderPanel()

    await screen.findByText(/we took 19 hours to respond/)

    expect(screen.queryByRole('textbox')).not.toBeInTheDocument()
    expect(document.querySelector('[contenteditable]')).toBeNull()
  })

  it('renders the generic failure message on a 422, never a partial draft', async () => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse({ detail: 'irrelevant' }, 422))
    renderPanel()

    expect(
      await screen.findByText("Couldn't generate a draft — try again."),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /copy draft/i })).not.toBeInTheDocument()
  })

  it('copy draft writes to the clipboard and stamps copied_at via the API', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(
        jsonResponse({
          id: 'draft-1',
          draft_text: 'Ana — we took 19 hours to respond; we promised 4.',
          tone_variant: 'direct',
          evidence_event_ids: ['evt-2'],
          checks_passed: true,
        }),
      )
      .mockResolvedValueOnce(new Response(null, { status: 204 }))
    renderPanel()

    await screen.findByText(/we took 19 hours to respond/)
    await userEvent.click(screen.getByRole('button', { name: 'Copy draft' }))

    await waitFor(() => expect(screen.getByRole('button', { name: 'Copied' })).toBeInTheDocument())
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      'Ana — we took 19 hours to respond; we promised 4.',
    )
    expect(apiFetch).toHaveBeenCalledWith('/api/drafts/draft-1/copy', { method: 'POST' })
  })
})

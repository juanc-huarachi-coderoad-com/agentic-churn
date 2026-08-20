import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from '../auth/api-client'
import { MeetingConsentPanel } from './meeting-consent-panel'
import type { ConsentListResponse } from './types'

vi.mock('../auth/api-client', () => ({
  apiFetch: vi.fn(),
}))

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status })
}

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MeetingConsentPanel />
    </QueryClientProvider>,
  )
}

const EMPTY_RESPONSE: ConsentListResponse = { series: [] }

describe('MeetingConsentPanel', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
  })

  it('renders the current consent status for each series', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({
        series: [
          {
            series_id: 'acme-weekly-sync',
            status: 'granted',
            all_parties_confirmed: true,
            documented_by: 'marta',
            documented_at: '2026-08-10T09:00:00Z',
            note: null,
          },
        ],
      } satisfies ConsentListResponse),
    )

    renderPanel()

    expect(await screen.findByText('acme-weekly-sync')).toBeInTheDocument()
    expect(screen.getByText('Granted')).toBeInTheDocument()
    expect(screen.getByText('by marta')).toBeInTheDocument()
  })

  it('blocks granting without confirming all parties consented', async () => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse(EMPTY_RESPONSE))

    renderPanel()
    await screen.findByText('No consent decisions recorded yet.')

    fireEvent.change(screen.getByLabelText('Meeting series'), {
      target: { value: 'acme-weekly-sync' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Save decision' }))

    expect(
      await screen.findByText('Confirm every participant consented before granting.'),
    ).toBeInTheDocument()
    // Only the initial GET happened — the invalid submission never reached the API.
    expect(apiFetch).toHaveBeenCalledTimes(1)
  })

  it('submits a grant and shows a 403 as an unavailable-action message, never a hidden form', async () => {
    // This app has no client-side knowledge of the signed-in user's role
    // (auth-store.ts stores only the bearer token) — the form always renders,
    // and a non-CS-lead's 403 surfaces here instead.
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(jsonResponse(EMPTY_RESPONSE))
      .mockResolvedValueOnce(jsonResponse({ detail: 'forbidden' }, 403))

    renderPanel()
    await screen.findByText('No consent decisions recorded yet.')

    fireEvent.change(screen.getByLabelText('Meeting series'), {
      target: { value: 'acme-weekly-sync' },
    })
    fireEvent.click(screen.getByLabelText(/I confirm every participant/))
    fireEvent.click(screen.getByRole('button', { name: 'Save decision' }))

    expect(
      await screen.findByText("This action isn't available for your account."),
    ).toBeInTheDocument()
  })

  it('resets the form after a successful submission', async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce(jsonResponse(EMPTY_RESPONSE))
      .mockResolvedValueOnce(
        jsonResponse({
          series_id: 'acme-weekly-sync',
          status: 'granted',
          all_parties_confirmed: true,
          documented_by: 'marta',
          documented_at: '2026-08-10T09:00:00Z',
          note: null,
        }),
      )
      .mockResolvedValueOnce(jsonResponse(EMPTY_RESPONSE))

    renderPanel()
    await screen.findByText('No consent decisions recorded yet.')

    const seriesInput = screen.getByLabelText('Meeting series') as HTMLInputElement
    fireEvent.change(seriesInput, { target: { value: 'acme-weekly-sync' } })
    fireEvent.click(screen.getByLabelText(/I confirm every participant/))
    fireEvent.click(screen.getByRole('button', { name: 'Save decision' }))

    await waitFor(() => expect(seriesInput.value).toBe(''))
  })
})

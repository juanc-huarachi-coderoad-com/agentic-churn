import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from '../auth/api-client'
import { CoveragePage } from './coverage-page'
import type { CoverageResponse } from './types'

vi.mock('../auth/api-client', () => ({
  apiFetch: vi.fn(),
}))

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status })
}

function renderCoverage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter initialEntries={['/coverage']}>
      <QueryClientProvider client={queryClient}>
        <CoveragePage />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

const BASE_RESPONSE: CoverageResponse = {
  sources: [{ source_type: 'email', status: 'connected', last_successful_sync_at: null }],
  quarantine: [],
}

const EMPTY_CONSENT = { series: [] }

// The consent panel (rendered unconditionally on this page too) makes its
// own GET /api/meeting-audio/consent call — a single blanket mock would
// hand it a CoverageResponse-shaped body instead, so every test here routes
// by URL instead.
function mockApiFetchByPath(handlers: Record<string, () => Response>) {
  vi.mocked(apiFetch).mockImplementation(async (path: string) => {
    for (const [prefix, handler] of Object.entries(handlers)) {
      if (path.startsWith(prefix)) return handler()
    }
    throw new Error(`Unmocked apiFetch call: ${path}`)
  })
}

describe('CoveragePage', () => {
  beforeEach(() => {
    mockApiFetchByPath({
      '/api/coverage': () => jsonResponse(BASE_RESPONSE),
      '/api/meeting-audio/consent': () => jsonResponse(EMPTY_CONSENT),
    })
  })

  it('renders the sidebar destinations alongside the system health content', async () => {
    renderCoverage()

    expect(await screen.findByText('System health')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Coverage' })).toHaveAttribute(
      'aria-current',
      'page',
    )
    expect(screen.getByRole('link', { name: 'Profile' })).toBeInTheDocument()
  })

  it('shows a visibly distinct label for a degraded source, never color alone', async () => {
    mockApiFetchByPath({
      '/api/coverage': () =>
        jsonResponse({
          sources: [
            { source_type: 'transcripts', status: 'degraded', last_successful_sync_at: null },
          ],
          quarantine: [],
        } satisfies CoverageResponse),
      '/api/meeting-audio/consent': () => jsonResponse(EMPTY_CONSENT),
    })

    renderCoverage()

    expect(await screen.findByText('Degraded')).toBeInTheDocument()
  })

  it('checking for new audio and finding nothing shows a clear "nothing new" message', async () => {
    mockApiFetchByPath({
      '/api/coverage': () => jsonResponse(BASE_RESPONSE),
      '/api/meeting-audio/consent': () => jsonResponse(EMPTY_CONSENT),
      '/api/meeting-audio/refresh': () =>
        jsonResponse({
          recordings_found: 0,
          transcribed: 0,
          skipped_no_consent: 0,
          failed: 0,
          coverage_report_id: 'abc',
          source_error: null,
        }),
    })

    renderCoverage()
    await screen.findByText('System health')

    fireEvent.click(screen.getByRole('button', { name: 'Check for new meeting audio' }))

    expect(await screen.findByText('Nothing new since the last check.')).toBeInTheDocument()
  })

  it('checking for new audio and finding a degraded source shows the source_error, not a generic error', async () => {
    mockApiFetchByPath({
      '/api/coverage': () => jsonResponse(BASE_RESPONSE),
      '/api/meeting-audio/consent': () => jsonResponse(EMPTY_CONSENT),
      '/api/meeting-audio/refresh': () =>
        jsonResponse({
          recordings_found: 0,
          transcribed: 0,
          skipped_no_consent: 0,
          failed: 0,
          coverage_report_id: 'abc',
          source_error: 'Google Drive authorization is no longer valid.',
        }),
    })

    renderCoverage()
    await screen.findByText('System health')

    fireEvent.click(screen.getByRole('button', { name: 'Check for new meeting audio' }))

    expect(
      await screen.findByText(
        "Couldn't check — Google Drive authorization is no longer valid.",
      ),
    ).toBeInTheDocument()
  })
})

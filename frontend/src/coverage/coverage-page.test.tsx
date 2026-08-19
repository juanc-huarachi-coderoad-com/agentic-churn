import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from '../auth/api-client'
import { CoveragePage } from './coverage-page'
import type { CoverageResponse } from './types'

vi.mock('../auth/api-client', () => ({
  apiFetch: vi.fn(),
}))

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200 })
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

describe('CoveragePage', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse(BASE_RESPONSE))
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
})

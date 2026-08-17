import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from '../auth/api-client'
import { ProfileEditorForm } from './profile-editor-form'

vi.mock('../auth/api-client', () => ({
  apiFetch: vi.fn(),
}))

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status })
}

function renderForm() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ProfileEditorForm />
    </QueryClientProvider>,
  )
}

const CURRENT_PROFILE = {
  version_number: 3,
  client_name: 'Meridian Logistics',
  renewal_date: '2026-11-08',
  contract_value_band: 'strategic',
  stakeholders: [
    { name: 'Ana Reyes', role: 'CTO', influence: 'sponsor', signs_renewal: true },
  ],
  product_areas: [{ key: 'tracking_api', criticality: 'critical' }],
  commitments: [{ type: 'first_response', threshold_business_hours: 4.0 }],
  exclusions: ['legal_threads'],
  communication_norms: 'Direct communicators.',
}

describe('ProfileEditorForm', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
  })

  it('renders the current profile data once loaded', async () => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse(CURRENT_PROFILE))
    renderForm()

    expect(await screen.findByDisplayValue('Meridian Logistics')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Direct communicators.')).toBeInTheDocument()
    expect(screen.getByDisplayValue('legal_threads')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Ana Reyes')).toBeInTheDocument()
    expect(screen.getByText('Version 3')).toBeInTheDocument()
  })

  it('submits a change via POST /api/profile', async () => {
    vi.mocked(apiFetch).mockImplementation(async (path) => {
      if (path === '/api/profile' && typeof path === 'string') {
        return jsonResponse({ ...CURRENT_PROFILE, version_number: 4 })
      }
      return jsonResponse(CURRENT_PROFILE)
    })
    renderForm()

    await screen.findByDisplayValue('Meridian Logistics')
    const clientInput = screen.getByLabelText('Client name')
    await userEvent.clear(clientInput)
    await userEvent.type(clientInput, 'Meridian Logistics Inc')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    expect(apiFetch).toHaveBeenCalledWith(
      '/api/profile',
      expect.objectContaining({ method: 'POST' }),
    )
    const postCall = vi
      .mocked(apiFetch)
      .mock.calls.find(([, init]) => (init as RequestInit | undefined)?.method === 'POST')
    const body = JSON.parse((postCall?.[1] as RequestInit).body as string) as {
      client: string
    }
    expect(body.client).toBe('Meridian Logistics Inc')
  })

  it('renders a 422 response as an inline error, not a crash', async () => {
    vi.mocked(apiFetch).mockImplementation(async (path, init) => {
      if (path === '/api/profile' && init?.method === 'POST') {
        return jsonResponse({ detail: 'at least one stakeholder must have signs_renewal' }, 422)
      }
      return jsonResponse(CURRENT_PROFILE)
    })
    renderForm()

    const clientInput = await screen.findByDisplayValue('Meridian Logistics')
    await userEvent.type(clientInput, ' Inc')
    await userEvent.click(screen.getByRole('button', { name: /save changes/i }))

    expect(await screen.findByText(/signs_renewal/i)).toBeInTheDocument()
  })
})

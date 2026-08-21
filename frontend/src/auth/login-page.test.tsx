import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from './api-client'
import { useAuthStore } from './auth-store'
import { LoginPage } from './login-page'

vi.mock('./api-client', () => ({
  apiFetch: vi.fn(),
}))

const navigateMock = vi.fn()
vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router')
  return { ...actual, useNavigate: () => navigateMock }
})

function jsonResponse(body: unknown, init: { status?: number; ok?: boolean } = {}): Response {
  const { status = 200, ok = status >= 200 && status < 300 } = init
  return { ok, status, json: async () => body } as Response
}

function renderLoginPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
    navigateMock.mockReset()
    useAuthStore.setState({ token: null, isAuthenticated: false })
  })

  // US1 — a branded, professional first impression (spec.md User Story 1).
  it('renders the AURA brand treatment and heading', () => {
    renderLoginPage()

    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument()
    expect(screen.getAllByText('AURA').length).toBeGreaterThan(0)
    expect(
      screen.getByText(/The signals were always there/),
    ).toBeInTheDocument()
  })

  // US2 — familiar, working sign-in behavior (spec.md User Story 2).
  it('shows inline validation errors on empty submit and makes no request', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByText('Username is required')).toBeInTheDocument()
    expect(screen.getByText('Password is required')).toBeInTheDocument()
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it('shows a single invalid-credentials error on a rejected login', async () => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse(null, { status: 401 }))
    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText('Username'), 'marta')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByText('Invalid username or password.')).toBeInTheDocument()
    expect(navigateMock).not.toHaveBeenCalled()
  })

  it('logs in and navigates to /dashboard on a successful login', async () => {
    vi.mocked(apiFetch).mockResolvedValue(
      jsonResponse({ token: 'a-real-token', expires_at: '2026-08-22T00:00:00Z' }),
    )
    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText('Username'), 'marta')
    await user.type(screen.getByLabelText('Password'), 'agentic-demo-2026')
    await user.click(screen.getByRole('button', { name: 'Log in' }))

    await waitFor(() => expect(navigateMock).toHaveBeenCalledWith('/dashboard'))
    expect(useAuthStore.getState().token).toBe('a-real-token')
  })

  it('clears the root error as soon as either field is edited', async () => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse(null, { status: 401 }))
    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText('Username'), 'marta')
    await user.type(screen.getByLabelText('Password'), 'wrong-password')
    await user.click(screen.getByRole('button', { name: 'Log in' }))
    expect(await screen.findByText('Invalid username or password.')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Password'), '!')

    expect(screen.queryByText('Invalid username or password.')).not.toBeInTheDocument()
  })

  // US3 — comfortable, accessible interaction (spec.md User Story 3).
  it('toggles password visibility and its accessible label', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    const passwordInput = screen.getByLabelText('Password')
    expect(passwordInput).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: 'Reveal characters' }))
    expect(passwordInput).toHaveAttribute('type', 'text')

    await user.click(screen.getByRole('button', { name: 'Hide characters' }))
    expect(passwordInput).toHaveAttribute('type', 'password')
  })

  it('marks an invalid field with aria-invalid', async () => {
    const user = userEvent.setup()
    renderLoginPage()

    await user.click(screen.getByRole('button', { name: 'Log in' }))

    expect(await screen.findByLabelText('Username')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByLabelText('Password')).toHaveAttribute('aria-invalid', 'true')
  })
})

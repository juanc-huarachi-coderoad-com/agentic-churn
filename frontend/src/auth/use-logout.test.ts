import { renderHook } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch } from './api-client'
import { useAuthStore } from './auth-store'
import { useLogout } from './use-logout'

vi.mock('./api-client', () => ({
  apiFetch: vi.fn(),
}))

const navigateMock = vi.fn()
vi.mock('react-router', async () => {
  const actual = await vi.importActual<typeof import('react-router')>('react-router')
  return { ...actual, useNavigate: () => navigateMock }
})

function jsonResponse(body: unknown, status = 204): Response {
  return new Response(body ? JSON.stringify(body) : null, { status })
}

function renderUseLogout() {
  return renderHook(() => useLogout(), { wrapper: MemoryRouter }).result
}

describe('useLogout', () => {
  beforeEach(() => {
    vi.mocked(apiFetch).mockReset()
    navigateMock.mockReset()
    useAuthStore.setState({ token: 'a-token', isAuthenticated: true })
  })

  it('revokes the token, clears local state, and navigates to /login', async () => {
    vi.mocked(apiFetch).mockResolvedValue(jsonResponse(null))

    await renderUseLogout().current()

    expect(apiFetch).toHaveBeenCalledWith(
      '/auth/logout',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().token).toBeNull()
    expect(navigateMock).toHaveBeenCalledWith('/login')
  })

  it('still clears local state and navigates even when the network call fails', async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error('offline'))

    await renderUseLogout().current()

    expect(useAuthStore.getState().isAuthenticated).toBe(false)
    expect(useAuthStore.getState().token).toBeNull()
    expect(navigateMock).toHaveBeenCalledWith('/login')
  })
})

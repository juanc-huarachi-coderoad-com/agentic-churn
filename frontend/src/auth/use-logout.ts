import { useNavigate } from 'react-router'
import { apiFetch } from './api-client'
import { useAuthStore } from './auth-store'

// research.md Decision 3 — an intentional "Log out" click revokes the token
// server-side (the backend's already-implemented, already-tested
// POST /auth/logout, contracts/README.md) before clearing local state. The
// network call is best-effort: the client-side clear is what actually removes
// access to protected screens (FR-004), so it must never block on — or be
// undone by — a failed/offline request.
export function useLogout() {
  const navigate = useNavigate()

  return async function logout() {
    try {
      await apiFetch('/auth/logout', { method: 'POST' })
    } catch {
      // Best-effort revocation — proceed with the local logout regardless.
    }
    useAuthStore.getState().logout()
    navigate('/login')
  }
}

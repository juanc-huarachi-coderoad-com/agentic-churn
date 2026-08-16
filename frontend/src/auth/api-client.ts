import { useAuthStore } from './auth-store'

// Matches API_PORT's default in docker-compose.yml/.env.example — a Vite build-time
// override (VITE_API_BASE_URL) covers a non-default port without a code change.
const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000'

export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = useAuthStore.getState().token
  const headers = new Headers(init.headers)
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })

  if (response.status === 401) {
    // A 401 anywhere means the stored token is no longer valid (expired, revoked, or
    // never existed) — clear it so ProtectedRoute redirects to /login on the next
    // render, rather than leaving the UI in a silently-broken authenticated state
    // (spec.md User Story 2, Acceptance Scenario 4).
    useAuthStore.getState().logout()
  }

  return response
}

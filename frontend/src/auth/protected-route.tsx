import type { ReactNode } from 'react'
import { Navigate } from 'react-router'
import { useAuthStore } from './auth-store'

interface ProtectedRouteProps {
  children: ReactNode
}

// UX only — the actual security boundary is the backend re-validating the bearer
// token on every request (constitution Full-Stack §5 "Zero Trust Validation").
export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return children
}

import { LayoutGrid, Radar, UserRound } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export interface Destination {
  to: string
  label: string
  icon: LucideIcon
}

// FR-001/FR-002 (Clarifications 2026-08-17): exactly the app's existing
// destinations, one icon each — no placeholder icons for pages that don't
// exist yet. Single source of truth (research.md Decision 6) so the sidebar's
// tooltips/active state and the breadcrumb's per-page icon/label can never
// drift apart (FR-011).
export const DESTINATIONS: Destination[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutGrid },
  { to: '/coverage', label: 'Coverage', icon: Radar },
  { to: '/profile', label: 'Profile', icon: UserRound },
]

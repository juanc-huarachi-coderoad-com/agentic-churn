import { LayoutGrid, Radar, UserRound } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { NavLink } from 'react-router'
import { Icon } from '../components/ui/icon'
import { cn } from '../lib/utils'

interface Destination {
  to: string
  label: string
  icon: LucideIcon
}

// FR-001/FR-002 (Clarifications 2026-08-17): exactly the app's existing
// destinations, one icon each — no placeholder icons for pages that don't
// exist yet.
const DESTINATIONS: Destination[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutGrid },
  { to: '/coverage', label: 'Coverage', icon: Radar },
  { to: '/profile', label: 'Profile', icon: UserRound },
]

export function Sidebar() {
  return (
    <nav
      aria-label="Primary"
      className="flex w-16 shrink-0 flex-col items-center gap-2 border-r border-neutral-200 bg-white py-6"
    >
      {DESTINATIONS.map((destination) => (
        <NavLink
          key={destination.to}
          to={destination.to}
          className={({ isActive }) =>
            cn(
              'flex h-10 w-10 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700',
              isActive && 'bg-neutral-100 text-neutral-900',
            )
          }
        >
          <Icon icon={destination.icon} size={20} />
          <span className="sr-only">{destination.label}</span>
        </NavLink>
      ))}
    </nav>
  )
}

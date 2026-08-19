import { ChevronRight, Home } from 'lucide-react'
import { Link, useLocation } from 'react-router'
import { Icon } from '../components/ui/icon'
import { DESTINATIONS } from './destinations'

const HOME_PATH = '/dashboard'

// research.md Decisions 6–7: Home is a fixed concept (own icon/label, links to
// /dashboard) distinct from the trailing segment, which reuses the same
// label/icon the sidebar tooltip uses for the current route (DESTINATIONS) so
// the two can never say different things for the same page (FR-011). On the
// Home screen itself, only the non-clickable "Home" label renders — no second,
// duplicate segment (FR-010/FR-012, Clarification 2026-08-19).
export function Breadcrumb() {
  const { pathname } = useLocation()

  if (pathname === HOME_PATH) {
    return (
      <nav
        aria-label="Breadcrumb"
        className="flex min-w-0 items-center gap-1.5 text-sm text-neutral-500"
      >
        <Icon icon={Home} size={14} />
        <span>Home</span>
      </nav>
    )
  }

  const current = DESTINATIONS.find((destination) => destination.to === pathname)

  return (
    <nav
      aria-label="Breadcrumb"
      className="flex min-w-0 items-center gap-1.5 text-sm text-neutral-500"
    >
      <Link to={HOME_PATH} className="flex shrink-0 items-center gap-1.5 hover:text-neutral-700">
        <Icon icon={Home} size={14} />
        <span>Home</span>
      </Link>

      {current && (
        <>
          <Icon icon={ChevronRight} size={14} className="shrink-0" />
          <span className="flex min-w-0 items-center gap-1.5 truncate text-neutral-900">
            <Icon icon={current.icon} size={14} className="shrink-0" />
            <span className="truncate">{current.label}</span>
          </span>
        </>
      )}
    </nav>
  )
}

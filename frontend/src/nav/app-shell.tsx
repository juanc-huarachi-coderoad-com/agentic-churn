import { Bell } from 'lucide-react'
import type { ReactNode } from 'react'
import { Icon } from '../components/ui/icon'
import { Breadcrumb } from './breadcrumb'
import { Sidebar } from './sidebar'

interface AppShellProps {
  children: ReactNode
}

// research.md Decision 5 — lifted verbatim out of dashboard-page.tsx's own layout markup,
// which was previously the only page to render <Sidebar/> at all. Coverage and the Client
// Profile screen had no navigation chrome whatsoever before this feature; using AppShell
// inside each page (rather than as a route-level wrapper in App.tsx) means a page's own
// loading/error early-returns still render inside it — the sidebar/account menu stays
// reachable even while a page's own data is still loading (FR-001, FR-010).
export function AppShell({ children }: AppShellProps) {
  return (
    <div className="flex h-screen flex-col bg-neutral-50 lg:flex-row lg:overflow-hidden">
      <Sidebar />

      <main className="flex min-w-0 flex-1 flex-col p-8 lg:overflow-hidden">
        <div className="flex shrink-0 items-center justify-between gap-3">
          <Breadcrumb />
          <div className="flex shrink-0 items-center gap-3">
            <span className="flex items-center gap-1.5 rounded-full border border-neutral-200 px-3 py-1.5 text-xs text-neutral-600">
              <span className="h-1.5 w-1.5 rounded-full bg-green-500" aria-hidden="true" />
              Live
            </span>
            <span className="relative flex h-9 w-9 items-center justify-center rounded-md border border-neutral-200 text-neutral-500">
              <Icon icon={Bell} size={16} />
            </span>
          </div>
        </div>
        <div className="mt-4 flex min-h-0 flex-1 flex-col">{children}</div>
      </main>
    </div>
  )
}

import { NavLink } from 'react-router'
import { Icon } from '../components/ui/icon'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../components/ui/tooltip'
import { cn } from '../lib/utils'
import { AccountMenu } from './account-menu'
import { DESTINATIONS } from './destinations'

export function Sidebar() {
  return (
    <nav
      aria-label="Primary"
      className="flex w-16 shrink-0 flex-col items-center gap-2 border-r border-neutral-200 bg-white py-6"
    >
      <TooltipProvider delayDuration={400}>
        {DESTINATIONS.map((destination) => (
          <Tooltip key={destination.to}>
            <TooltipTrigger asChild>
              <NavLink
                to={destination.to}
                className={({ isActive }) =>
                  cn(
                    'relative flex h-10 w-10 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700',
                    isActive && 'bg-neutral-100 text-neutral-900',
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    {/* FR-008: a shape cue, not just the background-color
                        change above — visible regardless of color vision. */}
                    {isActive && (
                      <span
                        aria-hidden="true"
                        data-active-indicator
                        className="absolute left-0 h-6 w-1 rounded-r bg-neutral-900"
                      />
                    )}
                    <Icon icon={destination.icon} size={20} />
                    <span className="sr-only">{destination.label}</span>
                  </>
                )}
              </NavLink>
            </TooltipTrigger>
            <TooltipContent side="right">{destination.label}</TooltipContent>
          </Tooltip>
        ))}
      </TooltipProvider>

      {/* FR-001: bottom-left, per base/mockup-mainPage-v2.jpg. */}
      <div className="mt-auto">
        <AccountMenu />
      </div>
    </nav>
  )
}

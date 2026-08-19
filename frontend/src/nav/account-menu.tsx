import { LogOut, User } from 'lucide-react'
import { useLogout } from '../auth/use-logout'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '../components/ui/dropdown-menu'
import { Icon } from '../components/ui/icon'

// FR-001/FR-002 (Clarifications 2026-08-19): a generic account icon — no
// photo, no online-status dot, since the app holds no user-identity data
// today — opening a menu whose only item is "Log out".
export function AccountMenu() {
  const logout = useLogout()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        aria-label="Account menu"
        className="flex h-10 w-10 items-center justify-center rounded-md text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
      >
        <Icon icon={User} size={20} />
      </DropdownMenuTrigger>
      <DropdownMenuContent side="right" align="end">
        <DropdownMenuItem
          onSelect={() => {
            void logout()
          }}
          className="flex items-center gap-2"
        >
          <Icon icon={LogOut} size={14} />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

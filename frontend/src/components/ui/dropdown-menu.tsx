import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'
import type { ComponentProps } from 'react'
import { cn } from '../../lib/utils'

// Minimal Radix DropdownMenu wrapper (research.md Decision 2) — same shape as
// dialog.tsx/tooltip.tsx. Chosen over Dialog (centered/backdrop-modal) or a hand-rolled
// popover because DropdownMenu already layers correct menu/menuitem ARIA roles, arrow-key
// navigation, and outside-click/Escape dismissal on top of Radix's positioning primitive —
// exactly what FR-005's "close on outside click or Escape without ending the session"
// needs, for free.
export const DropdownMenu = DropdownMenuPrimitive.Root
export const DropdownMenuTrigger = DropdownMenuPrimitive.Trigger

export function DropdownMenuContent({
  className,
  sideOffset = 8,
  children,
  ...props
}: ComponentProps<typeof DropdownMenuPrimitive.Content>) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          'z-50 min-w-[8rem] rounded-md border border-neutral-200 bg-white p-1 shadow-lg focus:outline-none',
          className,
        )}
        {...props}
      >
        {children}
      </DropdownMenuPrimitive.Content>
    </DropdownMenuPrimitive.Portal>
  )
}

export function DropdownMenuItem({
  className,
  ...props
}: ComponentProps<typeof DropdownMenuPrimitive.Item>) {
  return (
    <DropdownMenuPrimitive.Item
      className={cn(
        'cursor-pointer rounded px-2.5 py-1.5 text-sm text-neutral-700 outline-none select-none hover:bg-neutral-100 focus:bg-neutral-100',
        className,
      )}
      {...props}
    />
  )
}

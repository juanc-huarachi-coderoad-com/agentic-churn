import * as TooltipPrimitive from '@radix-ui/react-tooltip'
import type { ComponentProps } from 'react'
import { cn } from '../../lib/utils'

// Minimal Radix Tooltip wrapper (research.md Decision 1) — same shape as dialog.tsx: a
// thin, typed pass-through around the Radix primitive with the project's own styling
// classes, so keyboard-focus visibility, positioning, and Escape-dismiss all come from
// Radix rather than a hand-rolled hover timer.
export const TooltipProvider = TooltipPrimitive.Provider
export const Tooltip = TooltipPrimitive.Root
export const TooltipTrigger = TooltipPrimitive.Trigger

export function TooltipContent({
  className,
  sideOffset = 8,
  children,
  ...props
}: ComponentProps<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        sideOffset={sideOffset}
        className={cn(
          'z-50 rounded-md bg-neutral-900 px-2.5 py-1.5 text-xs text-white shadow-md',
          className,
        )}
        {...props}
      >
        {children}
      </TooltipPrimitive.Content>
    </TooltipPrimitive.Portal>
  )
}

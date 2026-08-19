import * as DialogPrimitive from '@radix-ui/react-dialog'
import type { ComponentProps } from 'react'
import { cn } from '../../lib/utils'

// Minimal Radix Dialog wrapper (research.md Decision 2) — only what
// EvidencePanel/DraftComposerPanel actually need: centered layout,
// backdrop-dismissible, focus-trapped, Esc-to-close (FR-013, FR-016), all
// via Radix's own built-in behavior rather than re-solved by hand. No
// Trigger export — both panels are opened from dashboard-page.tsx's own
// selection state, not a Radix-managed trigger element (P10 — no primitive
// built beyond what this feature needs).
export const Dialog = DialogPrimitive.Root
export const DialogClose = DialogPrimitive.Close

export function DialogOverlay({
  className,
  ...props
}: ComponentProps<typeof DialogPrimitive.Overlay>) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay
        data-testid="dialog-overlay"
        className={cn(
          'fixed inset-0 z-50 bg-neutral-900/30 transition-opacity duration-150',
          className,
        )}
        {...props}
      />
    </DialogPrimitive.Portal>
  )
}

export function DialogContent({
  className,
  children,
  ...props
}: ComponentProps<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Content
        className={cn(
          'fixed top-1/2 left-1/2 z-50 max-h-[85vh] w-full max-w-md -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-lg border border-neutral-200 bg-white p-6 shadow-xl transition-all duration-150 focus:outline-none',
          className,
        )}
        {...props}
      >
        {children}
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

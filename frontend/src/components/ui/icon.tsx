import type { LucideIcon } from 'lucide-react'
import { cn } from '../../lib/utils'

interface IconProps {
  icon: LucideIcon
  className?: string
  size?: number
  'aria-hidden'?: boolean
}

// Constitution v1.3.0, Full-Stack Engineering §2 "UI & Styling": icons MUST
// use lucide-react. This wrapper keeps size/stroke consistent everywhere
// (sidebar, hub badges, assistant launcher) instead of each call site
// picking its own values.
export function Icon({ icon: LucideIconComponent, className, size = 18, ...props }: IconProps) {
  return (
    <LucideIconComponent
      size={size}
      strokeWidth={1.75}
      className={cn('shrink-0', className)}
      aria-hidden={props['aria-hidden'] ?? true}
    />
  )
}

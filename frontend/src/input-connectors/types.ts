import type { LucideIcon } from 'lucide-react'

export type ConnectorStatus = 'live' | 'simulated' | 'planned'

// 'brand': a real downloaded logo file under public/icons/connectors/ (data-model.md
// Decision 1 — only for marks still in Simple Icons' actively-maintained CC0 index).
// 'lucide': a generic icon standing in for a connector, optionally tinted with that
// connector's own brand color via a Tailwind arbitrary-value class (e.g. "text-[#4A154B]").
export type ConnectorIcon =
  | { kind: 'brand'; asset: string; alt: string }
  | { kind: 'lucide'; icon: LucideIcon; tintClassName?: string }

export interface Connector {
  id: string
  name: string
  status: ConnectorStatus
  description: string
  pipeline?: string[]
  icon: ConnectorIcon
}

export interface ConnectorGroup {
  status: ConnectorStatus
  label: string
  connectors: Connector[]
}

import { ChevronRight } from 'lucide-react'
import { Icon } from '../components/ui/icon'
import { cn } from '../lib/utils'
import { BrandIcon } from './brand-icon'
import { StatusBadge } from './status-badge'
import type { Connector } from './types'

interface ConnectorIconTileProps {
  connector: Connector
}

function ConnectorIconTile({ connector }: ConnectorIconTileProps) {
  return (
    <div
      className={cn(
        'flex h-10 w-10 shrink-0 items-center justify-center rounded-lg',
        connector.status === 'live' ? 'bg-emerald-50' : 'bg-neutral-100',
      )}
    >
      {connector.icon.kind === 'brand' ? (
        <BrandIcon asset={connector.icon.asset} alt={connector.icon.alt} className="h-5 w-5" />
      ) : (
        <Icon icon={connector.icon.icon} size={20} className={connector.icon.tintClassName} />
      )}
    </div>
  )
}

interface ConnectorCardProps {
  connector: Connector
  // "row" (Live, spec.md's single-entry section) matches the mockup's wide detail row;
  // "tile" (Simulated/Planned) matches its grid of compact cards.
  variant?: 'row' | 'tile'
}

export function ConnectorCard({ connector, variant = 'tile' }: ConnectorCardProps) {
  if (variant === 'row') {
    return (
      <div className="flex items-center gap-4 rounded-xl border border-neutral-200 bg-white p-4">
        <ConnectorIconTile connector={connector} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium text-neutral-900">{connector.name}</span>
            <StatusBadge status={connector.status} />
          </div>
          <p className="mt-1 text-sm text-neutral-500">{connector.description}</p>
          {connector.pipeline && (
            <p className="mt-0.5 text-xs text-neutral-400">
              ({connector.pipeline.join(' + ')})
            </p>
          )}
        </div>
        <Icon icon={ChevronRight} size={18} className="shrink-0 text-neutral-300" />
      </div>
    )
  }

  return (
    <div className={cn('rounded-xl border border-neutral-200 bg-white p-4')}>
      <ConnectorIconTile connector={connector} />
      <p className="mt-3 font-medium text-neutral-900">{connector.name}</p>
      <p className="mt-1 text-xs text-neutral-500">{connector.description}</p>
      {connector.pipeline && (
        <p className="mt-0.5 text-[11px] text-neutral-400">({connector.pipeline.join(' + ')})</p>
      )}
      <div className="mt-2">
        <StatusBadge status={connector.status} />
      </div>
    </div>
  )
}

import type { StakeholderCard } from './types'

const STATUS_LABEL: Record<StakeholderCard['status'], string> = {
  active: 'Active',
  quiet: 'Quiet',
  unresolved_identity: 'Unresolved',
}

interface StakeholderCardsProps {
  cards: StakeholderCard[]
}

export function StakeholderCards({ cards }: StakeholderCardsProps) {
  if (cards.length === 0) {
    return null
  }

  return (
    <div>
      <p className="text-xs tracking-wide text-neutral-400 uppercase">Stakeholders</p>
      <ul className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
        {cards.map((card) => (
          <li
            key={card.stakeholder_id ?? card.name}
            className="rounded-lg border border-neutral-200 bg-white p-3"
          >
            <p className="text-sm font-medium text-neutral-900">{card.name}</p>
            <p className="text-xs text-neutral-500">{card.role}</p>
            <p className="mt-1 text-xs text-neutral-400">
              {STATUS_LABEL[card.status]}
              {card.last_seen_at &&
                ` · last seen ${new Date(card.last_seen_at).toLocaleDateString()}`}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}

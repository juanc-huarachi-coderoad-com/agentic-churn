import type { NarratorSummary } from './types'

interface NarratorPanelProps {
  narrator: NarratorSummary
}

// specs/008-narrator-and-ask-agent — the first time this dashboard shows a
// plain-language explanation of the score, closing the gap feature 006
// explicitly deferred (REQ-M8-01). Every reason/action here already passed
// the backend's mechanical fact-check (REQ-M7-06/07) — this component only
// renders what already exists, never generates or reorders anything itself.
export function NarratorPanel({ narrator }: NarratorPanelProps) {
  return (
    <section className="mt-6 rounded-md border border-neutral-200 bg-white p-5">
      <h2 className="text-base font-medium text-neutral-900">{narrator.headline}</h2>

      {narrator.reasons.length > 0 && (
        <ul className="mt-4 space-y-2">
          {narrator.reasons.map((reason) => (
            <li key={reason.text} className="flex items-baseline justify-between gap-4 text-sm">
              <span className="text-neutral-700">{reason.text}</span>
              <span className="shrink-0 tabular-nums text-neutral-400">
                {reason.points.toFixed(1)} pts
              </span>
            </li>
          ))}
        </ul>
      )}

      {narrator.actions.length > 0 && (
        <div className="mt-4 border-t border-neutral-100 pt-4">
          <p className="text-xs tracking-wide text-neutral-400 uppercase">Next steps</p>
          <ul className="mt-2 space-y-2">
            {narrator.actions.map((action) => (
              <li key={action.text} className="text-sm text-neutral-700">
                {action.text}
                <span className="ml-2 text-xs text-neutral-400">
                  {action.owner} · {action.due_date}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

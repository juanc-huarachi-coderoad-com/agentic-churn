import { useEvidence } from './use-evidence'

interface EvidencePanelProps {
  scoreContributionId: string | null
  onClose: () => void
}

// Client-side overlay on the same /dashboard route, not a route change
// (research.md's Decision — "opens from any number," base/...md §11.4).
// No feedback controls here — out of this feature's scope (FR-014, feature
// 010's job); no Ask bar either (feature 008's job).
export function EvidencePanel({ scoreContributionId, onClose }: EvidencePanelProps) {
  const { data, isLoading, isError } = useEvidence(scoreContributionId)

  if (scoreContributionId === null) {
    return null
  }

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-neutral-900/20"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-label="Evidence trace"
        className="h-full w-full max-w-md overflow-y-auto border-l border-neutral-200 bg-white p-6 shadow-xl"
        onClick={(event) => event.stopPropagation()}
      >
        <button type="button" onClick={onClose} className="text-sm text-neutral-500">
          Close
        </button>

        {isLoading && <p className="mt-6 text-sm text-neutral-500">Loading…</p>}
        {isError && (
          <p className="mt-6 text-sm text-red-600">Couldn't load this evidence — try again.</p>
        )}

        {data && (
          <>
            <h2 className="mt-4 text-lg font-medium text-neutral-900">
              {data.finding_type.replace(/_/g, ' ')}
            </h2>
            <p className="text-sm text-neutral-500">{data.points.toFixed(1)} points</p>

            <div className="mt-6 grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs tracking-wide text-neutral-400 uppercase">Normally</p>
                <p className="mt-1 text-sm text-neutral-800">{data.baseline_value}</p>
              </div>
              <div>
                <p className="text-xs tracking-wide text-neutral-400 uppercase">Now</p>
                <p className="mt-1 text-sm text-neutral-800">{data.current_value}</p>
              </div>
            </div>

            {data.what_changed.length > 0 && (
              <ul className="mt-6 list-disc space-y-1 pl-5 text-sm text-neutral-700">
                {data.what_changed.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            )}

            {data.quoted_messages.length > 0 && (
              <div className="mt-6 space-y-3">
                {data.quoted_messages.map((message) => (
                  <div key={message.event_id}>
                    {message.text && (
                      // Client-authored words, serif, quoted (REQ-M8-04).
                      <p className="font-serif text-sm text-neutral-800">
                        &ldquo;{message.text}&rdquo;
                      </p>
                    )}
                    <p className="text-xs text-neutral-400">
                      {new Date(message.occurred_at).toLocaleString()}
                    </p>
                  </div>
                ))}
              </div>
            )}

            <p className="mt-6 text-sm text-neutral-600">{data.arithmetic_explanation}</p>
          </>
        )}
      </div>
    </div>
  )
}

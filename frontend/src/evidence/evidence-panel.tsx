import { useEvidence } from './use-evidence'
import { type Verdict, useFeedback } from './use-feedback'

interface EvidencePanelProps {
  scoreContributionId: string | null
  onClose: () => void
}

const VERDICTS: { verdict: Verdict; label: string }[] = [
  { verdict: 'correct', label: 'Correct' },
  { verdict: 'false_alarm', label: 'False alarm' },
  { verdict: 'resolved', label: 'Resolved' },
]

// Client-side overlay on the same /dashboard route, not a route change
// (research.md's Decision — "opens from any number," base/...md §11.4).
// No Ask bar here (feature 008's job).
export function EvidencePanel({ scoreContributionId, onClose }: EvidencePanelProps) {
  const { data, isLoading, isError } = useEvidence(scoreContributionId)
  const feedback = useFeedback(scoreContributionId)

  if (scoreContributionId === null) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-neutral-900/20" onClick={onClose}>
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

            {data.disclosure_text && (
              // REQ-M4-04 — the pattern's current, plain-language reason.
              // Absent (not empty) whenever the pattern has never been
              // damped (constitution P6 — no manufactured signal).
              <p className="mt-4 text-sm text-amber-700">{data.disclosure_text}</p>
            )}

            {/* One click, no modal, no confirmation toast (FR-002). */}
            <div className="mt-6 flex gap-2">
              {VERDICTS.map(({ verdict, label }) => (
                <button
                  key={verdict}
                  type="button"
                  disabled={feedback.isPending}
                  onClick={() => feedback.mutate({ findingId: data.finding_id, verdict })}
                  className="rounded border border-neutral-300 px-3 py-1 text-sm text-neutral-700 hover:bg-neutral-50 disabled:opacity-50"
                >
                  {label}
                </button>
              ))}
            </div>
            {feedback.isError && (
              <p className="mt-2 text-sm text-red-600">Couldn't record that — try again.</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}

import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { useMeetingConsent, useRecordConsent } from './use-meeting-consent'

const consentFormSchema = z
  .object({
    series_id: z.string().min(1, 'Required'),
    status: z.enum(['granted', 'revoked']),
    all_parties_confirmed: z.boolean(),
    note: z.string().optional(),
  })
  // UX-only mirror of the backend's own rule (data-model.md's validation rule,
  // enforced for real at the adapter boundary — Zero Trust Validation,
  // constitution Full-Stack §5) — catches the mistake before a round trip,
  // never the only place it's enforced.
  .refine((values) => values.status !== 'granted' || values.all_parties_confirmed, {
    message: 'Confirm every participant consented before granting.',
    path: ['all_parties_confirmed'],
  })

type ConsentFormValues = z.infer<typeof consentFormSchema>

const DEFAULT_VALUES: ConsentFormValues = {
  series_id: '',
  status: 'granted',
  all_parties_confirmed: false,
  note: '',
}

// Meeting-series consent for audio ingestion (specs/019-meeting-audio-ingestion,
// FR-004/FR-005/FR-016) — rendered unconditionally for any authenticated user,
// the same convention profile-editor-form.tsx already follows: this app has no
// client-side knowledge of the signed-in user's role (auth-store.ts stores only
// the bearer token), so the backend's `require_full_access` gate is the real
// enforcement point, and a non-CS-lead submission surfaces as the mutation's
// own error state below, not a hidden form.
export function MeetingConsentPanel() {
  const { data, isLoading, isError } = useMeetingConsent()
  const recordConsent = useRecordConsent()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<ConsentFormValues>({
    resolver: zodResolver(consentFormSchema),
    defaultValues: DEFAULT_VALUES,
  })

  const onSubmit = handleSubmit((values) => {
    // `.mutate()`, not `.mutateAsync()` — the 403/422 failure path is fully
    // handled via `recordConsent.isError`/`.error` below; a `mutateAsync`
    // `await` here would also need its own try/catch for the identical
    // state TanStack Query already tracks, just to avoid an unhandled
    // rejection warning for a rethrow nothing here needs to act on.
    recordConsent.mutate(
      {
        series_id: values.series_id,
        status: values.status,
        all_parties_confirmed: values.all_parties_confirmed,
        note: values.note || null,
      },
      { onSuccess: () => reset(DEFAULT_VALUES) },
    )
  })

  return (
    <div className="mt-8">
      <h2 className="text-sm font-medium text-neutral-900">Meeting audio consent</h2>
      <p className="mt-1 text-sm text-neutral-500">
        A recording is only ever collected for a meeting series with an active, documented
        grant below.
      </p>

      {isLoading && <p className="mt-3 text-sm text-neutral-500">Loading…</p>}
      {isError && (
        <p className="mt-3 text-sm text-red-600">Couldn't load consent status — try again.</p>
      )}
      {data && (
        <ul className="mt-3 space-y-1 text-sm">
          {data.series.length === 0 && (
            <li className="text-neutral-500">No consent decisions recorded yet.</li>
          )}
          {data.series.map((entry) => (
            <li
              key={entry.series_id}
              className="flex items-center justify-between border-b border-neutral-100 pb-1"
            >
              <span className="text-neutral-800">{entry.series_id}</span>
              <span
                className={entry.status === 'granted' ? 'text-neutral-600' : 'text-red-600'}
              >
                {entry.status === 'granted' ? 'Granted' : 'Revoked'}
              </span>
              <span className="text-xs text-neutral-400">by {entry.documented_by}</span>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={(e) => void onSubmit(e)} className="mt-4 space-y-3 rounded border border-neutral-200 p-4">
        <div>
          <label htmlFor="series_id" className="block text-sm text-neutral-600">
            Meeting series
          </label>
          <input
            id="series_id"
            placeholder="e.g. acme-weekly-sync"
            className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
            {...register('series_id')}
          />
          {errors.series_id && (
            <p className="mt-1 text-sm text-red-600">{errors.series_id.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="status" className="block text-sm text-neutral-600">
            Decision
          </label>
          <select
            id="status"
            className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
            {...register('status')}
          >
            <option value="granted">Grant consent</option>
            <option value="revoked">Revoke consent</option>
          </select>
        </div>

        <div>
          <label className="flex items-center gap-2 text-sm text-neutral-600">
            <input type="checkbox" {...register('all_parties_confirmed')} />
            I confirm every participant in this series has consented to being recorded and
            analyzed.
          </label>
          {errors.all_parties_confirmed && (
            <p className="mt-1 text-sm text-red-600">{errors.all_parties_confirmed.message}</p>
          )}
        </div>

        <div>
          <label htmlFor="note" className="block text-sm text-neutral-600">
            Note (optional)
          </label>
          <textarea
            id="note"
            rows={2}
            className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
            {...register('note')}
          />
        </div>

        {recordConsent.isError && (
          <p className="text-sm text-red-600">
            {(recordConsent.error as { status?: number })?.status === 403
              ? "This action isn't available for your account."
              : 'Could not save this decision — check the form and try again.'}
          </p>
        )}

        <button
          type="submit"
          disabled={recordConsent.isPending}
          className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {recordConsent.isPending ? 'Saving…' : 'Save decision'}
        </button>
      </form>
    </div>
  )
}

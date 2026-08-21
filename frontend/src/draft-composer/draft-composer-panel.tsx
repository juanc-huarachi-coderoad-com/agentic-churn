import { useMutation } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogOverlay } from '../components/ui/dialog'
import { DraftCheckFailedError, copyDraft, logDraftAsSent, postDraft } from './api'
import type { ToneVariant } from './types'

interface DraftComposerPanelProps {
  scoreContributionId: string | null
  stakeholderId: string | null
  onClose: () => void
}

const TONE_VARIANTS: ToneVariant[] = ['direct', 'formal', 'brief']

// specs/009-draft-composer — "the closer." Opens beside the evidence
// (base/...md §11.2, read during /speckit-clarify as tone-variant selection
// and copy, not literal free-text editing — FR-009a). No edit control of
// any kind exists here, and no send action exists anywhere in this file or
// any other (REQ-M10-P1) — only "Copy draft" and "Log as sent (manual)".
export function DraftComposerPanel({
  scoreContributionId,
  stakeholderId,
  onClose,
}: DraftComposerPanelProps) {
  const [tone, setTone] = useState<ToneVariant>('direct')
  // Tracked by draft id, not a plain boolean, so "copied"/"logged" naturally
  // reset for a newly-generated draft (a different id) without an effect
  // needing to reset any state imperatively.
  const [copiedDraftId, setCopiedDraftId] = useState<string | null>(null)
  const [loggedDraftId, setLoggedDraftId] = useState<string | null>(null)

  const generate = useMutation({
    mutationFn: postDraft,
  })

  useEffect(() => {
    if (scoreContributionId && stakeholderId) {
      generate.mutate({
        score_contribution_id: scoreContributionId,
        stakeholder_id: stakeholderId,
        tone_variant: tone,
      })
    }
    // Only re-generate when the target or tone changes — not on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scoreContributionId, stakeholderId, tone])

  const copyMutation = useMutation({
    mutationFn: async () => {
      if (generate.data) {
        await navigator.clipboard.writeText(generate.data.draft_text)
        await copyDraft(generate.data.id)
      }
      return generate.data?.id ?? null
    },
    onSuccess: (draftId) => setCopiedDraftId(draftId),
  })

  const logMutation = useMutation({
    mutationFn: async () => {
      if (generate.data) {
        await logDraftAsSent(generate.data.id)
      }
      return generate.data?.id ?? null
    },
    onSuccess: (draftId) => setLoggedDraftId(draftId),
  })

  const copied = generate.data !== undefined && copiedDraftId === generate.data.id
  const loggedAsSent = generate.data !== undefined && loggedDraftId === generate.data.id

  if (scoreContributionId === null || stakeholderId === null) {
    return null
  }

  const checkFailed = generate.isError && generate.error instanceof DraftCheckFailedError

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogOverlay />
      <DialogContent aria-label="Draft composer">
        <button type="button" onClick={onClose} className="text-sm text-neutral-500">
          Close
        </button>

        <h2 className="mt-4 text-lg font-medium text-neutral-900">Draft a message</h2>

        <div className="mt-4 flex gap-2" role="tablist" aria-label="Tone">
          {TONE_VARIANTS.map((variant) => (
            <button
              key={variant}
              type="button"
              role="tab"
              aria-selected={tone === variant}
              onClick={() => setTone(variant)}
              className={
                tone === variant
                  ? 'rounded-md bg-neutral-900 px-3 py-1 text-sm text-white'
                  : 'rounded-md border border-neutral-200 px-3 py-1 text-sm text-neutral-600'
              }
            >
              {variant}
            </button>
          ))}
        </div>

        {generate.isPending && <p className="mt-6 text-sm text-neutral-500">Drafting…</p>}

        {checkFailed && (
          <p className="mt-6 text-sm text-red-600">Couldn't generate a draft — try again.</p>
        )}
        {generate.isError && !checkFailed && (
          <p className="mt-6 text-sm text-red-600">Something went wrong — try again.</p>
        )}

        {generate.data && (
          <>
            {/* Read-only — no <textarea>, no contentEditable, no edit action
                of any kind (FR-009a, Clarifications 2026-08-16). */}
            <p className="mt-6 font-serif text-sm whitespace-pre-wrap text-neutral-800">
              {generate.data.draft_text}
            </p>

            <div className="mt-6 flex gap-3">
              <button
                type="button"
                onClick={() => copyMutation.mutate()}
                className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white"
              >
                {copied ? 'Copied' : 'Copy draft'}
              </button>
              <button
                type="button"
                onClick={() => logMutation.mutate()}
                className="rounded-md border border-neutral-200 px-4 py-2 text-sm text-neutral-700"
              >
                {loggedAsSent ? 'Logged as sent' : 'Log as sent (manual)'}
              </button>
            </div>
            {/* No third action here, ever — there is no send capability
                anywhere in this product (REQ-M10-P1). */}
          </>
        )}
      </DialogContent>
    </Dialog>
  )
}

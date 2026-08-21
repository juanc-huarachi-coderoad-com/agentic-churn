import { MarkdownText } from './markdown-text'
import type { AskAnsweredResponse, ComponentResponsePart } from '../types'

interface AnswerRendererProps {
  answer: AskAnsweredResponse
  onOpenDraftComposer?: (scoreContributionId: string, stakeholderId: string) => void
  onOpenEvidence?: (scoreContributionId: string) => void
}

// specs/014-ask-agent-response-formats — an answered response is an
// ordered `parts` sequence: one part for text_only, two (text then
// component) for hybrid — the default for every structured-intent
// question as of specs/023-ask-agent-default-hybrid-responses, degrading
// to a lone component part only if text generation failed server-side.
// Each part renders independently, in order; nothing here reorders or
// merges parts (REQ-M9-03's discipline, extended). No change needed here
// for specs/023 — this renderer already handles every parts shape
// generically.
export function AnswerRenderer({
  answer,
  onOpenDraftComposer,
  onOpenEvidence,
}: AnswerRendererProps) {
  return (
    <div className="space-y-4">
      {answer.parts.map((part, index) =>
        part.type === 'text' ? (
          <MarkdownText key={index} markdown={part.markdown} />
        ) : (
          <GenerativeUIComponent
            key={index}
            part={part}
            onOpenDraftComposer={onOpenDraftComposer}
            onOpenEvidence={onOpenEvidence}
          />
        ),
      )}
    </div>
  )
}

interface GenerativeUIComponentProps {
  part: ComponentResponsePart
  onOpenDraftComposer?: (scoreContributionId: string, stakeholderId: string) => void
  onOpenEvidence?: (scoreContributionId: string) => void
}

// One renderer per closed-set component type (REQ-M9-02) — the Ask agent
// never answers a component part with a paragraph, only one of these fixed
// shapes. Every branch below reads only fields the backend already
// computed; nothing here generates or reorders anything itself (REQ-M9-03).
function GenerativeUIComponent({
  part,
  onOpenDraftComposer,
  onOpenEvidence,
}: GenerativeUIComponentProps) {
  const props = part.component_props

  switch (part.component) {
    case 'delta_breakdown':
      return <DeltaBreakdown props={props} onOpenEvidence={onOpenEvidence} />
    case 'baseline_comparison':
      return <BaselineComparison props={props} />
    case 'stakeholder_cards':
      return <StakeholderList props={props} />
    case 'ranked_issues':
      return <RankedIssues props={props} onOpenEvidence={onOpenEvidence} />
    case 'action_checklist':
      return <ActionChecklist props={props} />
    case 'commitments_status':
      return <CommitmentsStatus props={props} />
    case 'filtered_timeline':
      return <FilteredTimeline props={props} />
    case 'draft_handoff':
      return <DraftHandoff props={props} onOpenDraftComposer={onOpenDraftComposer} />
  }
}

interface Cause {
  finding_type: string
  points: number
  is_positive: boolean
  // Already present in the backend response (app.experience.adapters.
  // ask_agent_graph.py's query_score_runs); simply wasn't typed/read on the
  // frontend until feature 010 needed it for the evidence click-through
  // (specs/010-feedback-memory/research.md Decision 3).
  score_contribution_id: string
}

function DeltaBreakdown({
  props,
  onOpenEvidence,
}: {
  props: Record<string, unknown>
  onOpenEvidence?: (scoreContributionId: string) => void
}) {
  const causes = (props.causes as Cause[] | undefined) ?? []
  return (
    <div className="space-y-2">
      <p className="text-sm text-neutral-500">
        Score {String(props.score)} — {String(props.band).replace('_', ' ')}
      </p>
      <ul className="space-y-1">
        {causes.map((cause) => (
          <li key={cause.score_contribution_id}>
            <button
              type="button"
              disabled={!onOpenEvidence}
              onClick={() => onOpenEvidence?.(cause.score_contribution_id)}
              className="flex w-full justify-between text-left text-sm disabled:cursor-default"
            >
              <span className="text-neutral-700">{cause.finding_type.replace(/_/g, ' ')}</span>
              <span className={cause.is_positive ? 'text-green-700' : 'text-red-700'}>
                {cause.points > 0 ? '+' : ''}
                {cause.points.toFixed(1)}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

function BaselineComparison({ props }: { props: Record<string, unknown> }) {
  const messages = (props.current_messages as string[] | undefined) ?? []
  return (
    <div className="space-y-2 text-sm">
      <p className="text-neutral-500">
        Baseline built from {String(props.baseline_sample_count)} prior messages
      </p>
      {messages.map((message, index) => (
        <p key={index} className="font-serif text-neutral-800">
          &ldquo;{message}&rdquo;
        </p>
      ))}
    </div>
  )
}

interface StakeholderRow {
  name: string
  role: string
  last_seen_at: string | null
}

function StakeholderList({ props }: { props: Record<string, unknown> }) {
  const stakeholders = (props.stakeholders as StakeholderRow[] | undefined) ?? []
  return (
    <ul className="space-y-2">
      {stakeholders.map((s) => (
        <li key={s.name} className="text-sm">
          <span className="text-neutral-800">{s.name}</span>
          <span className="ml-2 text-neutral-400">{s.role}</span>
          {s.last_seen_at && (
            <span className="ml-2 text-xs text-neutral-400">
              last seen {new Date(s.last_seen_at).toLocaleDateString()}
            </span>
          )}
        </li>
      ))}
    </ul>
  )
}

function RankedIssues({
  props,
  onOpenEvidence,
}: {
  props: Record<string, unknown>
  onOpenEvidence?: (scoreContributionId: string) => void
}) {
  const issues = (props.ranked_issues as Cause[] | undefined) ?? []
  return (
    <ol className="list-decimal space-y-1 pl-5 text-sm">
      {issues.map((issue) => (
        <li key={issue.score_contribution_id}>
          <button
            type="button"
            disabled={!onOpenEvidence}
            onClick={() => onOpenEvidence?.(issue.score_contribution_id)}
            className="text-left text-neutral-700 disabled:cursor-default"
          >
            {issue.finding_type.replace(/_/g, ' ')}{' '}
            <span className="text-neutral-400">({Math.abs(issue.points).toFixed(1)} pts)</span>
          </button>
        </li>
      ))}
    </ol>
  )
}

interface ActionRow {
  text: string
  owner: string
  due_date: string
}

function ActionChecklist({ props }: { props: Record<string, unknown> }) {
  const actions = (props.actions as ActionRow[] | undefined) ?? []
  return (
    <ul className="space-y-2 text-sm">
      {actions.map((action) => (
        <li key={action.text} className="text-neutral-700">
          {action.text}
          <span className="ml-2 text-xs text-neutral-400">
            {action.owner} · {action.due_date}
          </span>
        </li>
      ))}
    </ul>
  )
}

interface CommitmentRow {
  text: string | null
  state: string
}

function CommitmentsStatus({ props }: { props: Record<string, unknown> }) {
  const commitments = (props.commitments as CommitmentRow[] | undefined) ?? []
  return (
    <ul className="space-y-2 text-sm">
      {commitments.map((c, index) => (
        <li key={index} className="text-neutral-700">
          {c.text ?? '(no text)'} <span className="text-neutral-400">— {c.state}</span>
        </li>
      ))}
    </ul>
  )
}

interface TimelineRow {
  event_id: string
  occurred_at: string
  text: string
}

function FilteredTimeline({ props }: { props: Record<string, unknown> }) {
  const events = (props.events as TimelineRow[] | undefined) ?? []
  return (
    <ul className="space-y-3 text-sm">
      {events.map((event) => (
        <li key={event.event_id}>
          <p className="font-serif text-neutral-800">&ldquo;{event.text}&rdquo;</p>
          <p className="text-xs text-neutral-400">{new Date(event.occurred_at).toLocaleString()}</p>
        </li>
      ))}
    </ul>
  )
}

// The one non-inline-answer case (FR-012a) — surfaces the handoff context
// rather than composing a message itself (feature 009's job). Real trigger
// as of feature 009 (research.md Decision 10) — a link when both
// score_contribution_id and stakeholder_id resolved. Below that, this must
// NOT still say "open the draft composer" (2026-08-21 amendment) — that
// text used to render unconditionally even when nothing was openable
// (live-tested against demo-wara: `score_contribution_id` was null on
// every question asked, since `issues`/`finding_issue_map` never gets
// populated by any live code path), which is a broken promise, not a
// fallback. Two distinct honest states replace it instead.
function DraftHandoff({
  props,
  onOpenDraftComposer,
}: {
  props: Record<string, unknown>
  onOpenDraftComposer?: (scoreContributionId: string, stakeholderId: string) => void
}) {
  const scoreContributionId = props.score_contribution_id as string | null | undefined
  const stakeholderId = props.stakeholder_id as string | null | undefined

  if (scoreContributionId && stakeholderId && onOpenDraftComposer) {
    return (
      <p className="text-sm text-neutral-600">
        Ready to draft a message about this —{' '}
        <button
          type="button"
          onClick={() => onOpenDraftComposer(scoreContributionId, stakeholderId)}
          className="font-medium text-neutral-900 underline"
        >
          open the draft composer
        </button>
        .
      </p>
    )
  }

  if (!stakeholderId) {
    return (
      <p className="text-sm text-neutral-600">
        Couldn't identify who to write to — try naming the stakeholder directly.
      </p>
    )
  }

  return (
    <p className="text-sm text-neutral-600">
      There's no specific risk finding to draft a message about right now.
    </p>
  )
}

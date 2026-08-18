import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AnswerRenderer } from './answer-renderer'
import type { AskAnsweredResponse } from '../types'

// specs/013-dashboard-reliability-fixes — real backend data can legitimately
// contain multiple causes with the same finding_type (two separate
// broken_response_promise findings); each row must still render distinctly
// and key by its own unique score_contribution_id, not the repeatable
// finding_type (research.md Decision 1).
//
// specs/014-ask-agent-response-formats — the answered response is now a
// `parts` sequence; component_only responses are always exactly one
// component part carrying this same data (Decision 5's backward-
// compatibility guarantee).
const DUPLICATE_FINDING_TYPE_ANSWER: AskAnsweredResponse = {
  intent: 'score_delta',
  parts: [
    {
      type: 'component',
      component: 'delta_breakdown',
      component_props: {
        score: 85.6,
        band: 'at_risk',
        causes: [
          {
            finding_type: 'broken_response_promise',
            points: 30.6,
            is_positive: false,
            score_contribution_id: 'contribution-1',
          },
          {
            finding_type: 'broken_response_promise',
            points: 40.0,
            is_positive: false,
            score_contribution_id: 'contribution-2',
          },
        ],
      },
    },
  ],
}

describe('AnswerRenderer — DeltaBreakdown', () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  afterEach(() => {
    consoleErrorSpy.mockRestore()
  })

  it('renders every cause as a distinct row even when finding_type repeats', () => {
    render(<AnswerRenderer answer={DUPLICATE_FINDING_TYPE_ANSWER} />)

    expect(screen.getByText('+30.6')).toBeInTheDocument()
    expect(screen.getByText('+40.0')).toBeInTheDocument()
    expect(screen.getAllByText('broken response promise')).toHaveLength(2)
  })

  it('opens evidence for the specific row clicked, never the other one with the same finding_type', async () => {
    const onOpenEvidence = vi.fn()
    render(
      <AnswerRenderer answer={DUPLICATE_FINDING_TYPE_ANSWER} onOpenEvidence={onOpenEvidence} />,
    )

    const rows = screen.getAllByRole('button')
    await userEvent.click(rows[1])

    expect(onOpenEvidence).toHaveBeenCalledExactlyOnceWith('contribution-2')
  })

  it('never warns about non-unique list keys when finding_type repeats', () => {
    render(<AnswerRenderer answer={DUPLICATE_FINDING_TYPE_ANSWER} />)

    const keyWarnings = consoleErrorSpy.mock.calls.filter((call: unknown[]) =>
      String(call[0]).match(/unique.*key/i),
    )
    expect(keyWarnings).toHaveLength(0)
  })
})

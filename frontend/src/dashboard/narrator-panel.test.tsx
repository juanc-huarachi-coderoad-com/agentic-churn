import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { NarratorPanel } from './narrator-panel'
import type { NarratorSummary } from './types'

const NARRATOR: NarratorSummary = {
  headline: 'We took 19 hours to reply — we promised 4 — and Ana is pulling back.',
  reasons: [
    {
      text: 'We took 19 hours to reply to ticket #456 — we promised 4.',
      points: 39.0,
      evidence_event_ids: ['45765fc1-57e9-444b-b73d-1cfbd1e0ea70'],
    },
  ],
  actions: [
    { text: 'Escalate #456 with engineering today', owner: 'Marta', due_date: '2026-08-16' },
  ],
}

describe('NarratorPanel', () => {
  it('renders the headline, reasons with points, and actions with owner/date', () => {
    render(<NarratorPanel narrator={NARRATOR} />)

    expect(
      screen.getByText('We took 19 hours to reply — we promised 4 — and Ana is pulling back.'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('We took 19 hours to reply to ticket #456 — we promised 4.'),
    ).toBeInTheDocument()
    expect(screen.getByText('39.0 pts')).toBeInTheDocument()
    expect(screen.getByText('Escalate #456 with engineering today')).toBeInTheDocument()
    expect(screen.getByText('Marta · 2026-08-16')).toBeInTheDocument()
  })

  it('renders no reasons/actions sections when both are empty — no placeholder content', () => {
    render(<NarratorPanel narrator={{ ...NARRATOR, reasons: [], actions: [] }} />)

    expect(screen.queryByText('Next steps')).not.toBeInTheDocument()
  })
})

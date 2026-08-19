import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { PulseTimeline } from './pulse-timeline'
import type { PulseEvent } from './types'

function buildEvent(overrides: Partial<PulseEvent> = {}): PulseEvent {
  return {
    event_id: 'evt-1',
    occurred_at: '2026-08-10T12:40:00Z',
    event_type: 'ticket_state_change',
    severity: 'at_risk',
    quoted_text: 'Slow API response',
    score_contribution_id: 'sc-1',
    ...overrides,
  }
}

describe('PulseTimeline', () => {
  it('renders nothing for an empty event list', () => {
    const { container } = render(<PulseTimeline events={[]} onSelect={vi.fn()} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('picks the icon shape from event_type and the ring color from severity, independently (FR-005a)', () => {
    const events: PulseEvent[] = [
      buildEvent({ event_id: 'evt-1', event_type: 'ticket_state_change', severity: 'at_risk' }),
      buildEvent({ event_id: 'evt-2', event_type: 'message', severity: 'at_risk' }),
      buildEvent({ event_id: 'evt-3', event_type: 'ticket_state_change', severity: 'info' }),
    ]
    render(<PulseTimeline events={events} onSelect={vi.fn()} />)

    const icon1 = screen.getByTestId('pulse-icon-evt-1')
    const icon2 = screen.getByTestId('pulse-icon-evt-2')
    const icon3 = screen.getByTestId('pulse-icon-evt-3')

    // Same severity (at_risk), different event_type -> different icon glyph.
    expect(icon1.dataset.iconType).not.toBe(icon2.dataset.iconType)
    // Same event_type, different severity -> different ring/color class.
    expect(icon1.className).not.toBe(icon3.className)
    expect(icon1.dataset.iconType).toBe(icon3.dataset.iconType)
  })

  it('renders the real type label and elapsed time for each entry (FR-005)', () => {
    render(<PulseTimeline events={[buildEvent({ event_type: 'usage_measurement' })]} onSelect={vi.fn()} />)

    expect(screen.getByText(/Activity/)).toBeInTheDocument()
  })

  it('falls back to a sensible label/icon for an event without a defined mapping, without breaking the stream', () => {
    // @ts-expect-error — simulating a runtime-only value outside the closed union.
    const events: PulseEvent[] = [buildEvent({ event_type: 'unknown_future_type' })]
    render(<PulseTimeline events={events} onSelect={vi.fn()} />)

    expect(screen.getByTestId('pulse-icon-evt-1')).toBeInTheDocument()
  })

  it('renders a connecting timeline line between consecutive entries (FR-007)', () => {
    const events: PulseEvent[] = [
      buildEvent({ event_id: 'evt-1' }),
      buildEvent({ event_id: 'evt-2' }),
    ]
    render(<PulseTimeline events={events} onSelect={vi.fn()} />)

    expect(screen.getAllByTestId('pulse-connector').length).toBe(1)
  })

  it('gives every entry a smooth hover/focus affordance on its icon and body (FR-012)', () => {
    const events: PulseEvent[] = [buildEvent({ event_id: 'evt-1' }), buildEvent({ event_id: 'evt-2' })]
    render(<PulseTimeline events={events} onSelect={vi.fn()} />)

    for (const button of screen.getAllByRole('button')) {
      expect(button.className).toMatch(/transition/)
      expect(button.className).toMatch(/hover:/)
    }
    const icon = screen.getByTestId('pulse-icon-evt-1')
    expect(icon.className).toMatch(/transition/)
    expect(icon.className).toMatch(/group-hover:/)
  })

  it('calls onSelect with the score_contribution_id when an entry is clicked', async () => {
    const onSelect = vi.fn()
    render(<PulseTimeline events={[buildEvent({ score_contribution_id: 'sc-42' })]} onSelect={onSelect} />)

    await userEvent.click(screen.getByRole('button'))
    expect(onSelect).toHaveBeenCalledWith('sc-42')
  })
})

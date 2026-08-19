import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ActionDraftHub } from './action-draft-hub'
import type { ContributionBar } from './types'

const BARS: ContributionBar[] = [
  {
    score_contribution_id: 'sc-1',
    label: 'broken_response_promise',
    points: 39.0,
    is_positive: false,
  },
  {
    score_contribution_id: 'sc-2',
    label: 'onboarding_milestone_hit',
    points: 8.0,
    is_positive: true,
  },
]

describe('ActionDraftHub', () => {
  it('renders nothing for an empty bar list', () => {
    const { container } = render(<ActionDraftHub bars={[]} onSelect={vi.fn()} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders ranked entries and calls onSelect with the score_contribution_id when clicked', async () => {
    const onSelect = vi.fn()
    render(<ActionDraftHub bars={BARS} onSelect={onSelect} />)

    await userEvent.click(screen.getByText('broken response promise'))
    expect(onSelect).toHaveBeenCalledWith('sc-1')
  })

  it('gives every selectable item a smooth hover/focus affordance on its icon and body (FR-012)', () => {
    render(<ActionDraftHub bars={BARS} onSelect={vi.fn()} />)

    const buttons = screen.getAllByRole('button')
    expect(buttons.length).toBeGreaterThan(0)
    for (const button of buttons) {
      expect(button.className).toMatch(/transition/)
      expect(button.className).toMatch(/hover:/)
      const icon = button.querySelector('[aria-hidden="true"]')
      expect(icon).not.toBeNull()
      expect(icon?.className).toMatch(/transition/)
      expect(icon?.className).toMatch(/group-hover:/)
    }
  })
})

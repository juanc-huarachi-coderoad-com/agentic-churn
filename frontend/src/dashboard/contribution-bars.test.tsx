import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ContributionBars } from './contribution-bars'
import type { ContributionBar } from './types'

const DUPLICATE_LABEL_BARS: ContributionBar[] = [
  { score_contribution_id: 'a', label: 'escalation_language', points: 16, is_positive: false },
  { score_contribution_id: 'b', label: 'escalation_language', points: 19, is_positive: false },
  { score_contribution_id: 'c', label: 'contact_absence', points: 8, is_positive: false },
]

describe('ContributionBars', () => {
  it('renders nothing when there are no bars', () => {
    const { container } = render(<ContributionBars bars={[]} onSelect={() => {}} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('collapses duplicate labels into one row with a count badge', () => {
    render(<ContributionBars bars={DUPLICATE_LABEL_BARS} onSelect={() => {}} />)

    expect(screen.getAllByText('escalation language')).toHaveLength(1)
    expect(screen.getByText('×2')).toBeInTheDocument()
    expect(screen.getByText('contact absence')).toBeInTheDocument()
  })

  it('calls onSelect with the id directly for a label with a single finding', async () => {
    const onSelect = vi.fn()
    render(<ContributionBars bars={DUPLICATE_LABEL_BARS} onSelect={onSelect} />)

    await userEvent.click(screen.getByText('contact absence'))
    expect(onSelect).toHaveBeenCalledExactlyOnceWith('c')
  })

  it('expands a grouped row and calls onSelect with the specific instance clicked', async () => {
    const onSelect = vi.fn()
    render(<ContributionBars bars={DUPLICATE_LABEL_BARS} onSelect={onSelect} />)

    await userEvent.click(screen.getByText('escalation language'))
    const subRows = screen.getAllByText('escalation language')
    expect(subRows).toHaveLength(3) // group row + 2 expanded sub-rows

    await userEvent.click(subRows[2])
    expect(onSelect).toHaveBeenCalledExactlyOnceWith('b')
  })
})

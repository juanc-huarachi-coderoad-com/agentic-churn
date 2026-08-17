import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ScoreBlock } from './score-block'

describe('ScoreBlock', () => {
  it('renders the score and band label', () => {
    render(<ScoreBlock score={65} band="at_risk" trend={[40, 50, 65]} onClick={() => {}} />)

    expect(screen.getByText('at risk')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Score detail' })).toBeInTheDocument()
  })

  it('calls onClick when the score is selected', async () => {
    const onClick = vi.fn()
    render(<ScoreBlock score={65} band="watch" trend={[40, 65]} onClick={onClick} />)

    await userEvent.click(screen.getByRole('button', { name: 'Score detail' }))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('renders the area chart when there are at least two trend points', () => {
    render(<ScoreBlock score={65} band="healthy" trend={[40, 50, 65]} onClick={() => {}} />)

    expect(screen.getByTestId('score-trend-chart')).toBeInTheDocument()
  })

  it('degrades gracefully with fewer than two trend points, instead of a broken chart', () => {
    render(<ScoreBlock score={65} band="healthy" trend={[65]} onClick={() => {}} />)

    expect(screen.queryByTestId('score-trend-chart')).not.toBeInTheDocument()
    expect(screen.getByText('Not enough history yet')).toBeInTheDocument()
  })

  it('renders neither a chart nor the "not enough history" note with zero trend points', () => {
    render(<ScoreBlock score={65} band="healthy" trend={[]} onClick={() => {}} />)

    expect(screen.queryByTestId('score-trend-chart')).not.toBeInTheDocument()
    expect(screen.queryByText('Not enough history yet')).not.toBeInTheDocument()
  })
})

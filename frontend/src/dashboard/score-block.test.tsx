import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeAll, describe, expect, it, vi } from 'vitest'
import { ScoreBlock } from './score-block'

// Recharts' <ResponsiveContainer> measures its DOM node via ResizeObserver
// and offsetWidth/offsetHeight, both effectively zero under jsdom — without
// this, the chart never lays out real ticks and FR-010's axis-label
// assertions below would false-negative regardless of the component code.
beforeAll(() => {
  Object.defineProperty(HTMLElement.prototype, 'offsetWidth', {
    configurable: true,
    value: 400,
  })
  Object.defineProperty(HTMLElement.prototype, 'offsetHeight', {
    configurable: true,
    value: 200,
  })
  HTMLElement.prototype.getBoundingClientRect = (): DOMRect => ({
    width: 400,
    height: 200,
    top: 0,
    left: 0,
    right: 400,
    bottom: 200,
    x: 0,
    y: 0,
    toJSON: () => {},
  })
  // Recharts' own type defs reference the DOM lib's global `ResizeObserver` —
  // jsdom has none, so this test-local stand-in is assigned via a typed
  // global augmentation, not `any`.
  globalThis.ResizeObserver = class {
    private readonly callback: ResizeObserverCallback
    constructor(callback: ResizeObserverCallback) {
      this.callback = callback
    }
    observe(target: Element) {
      this.callback(
        [{ target, contentRect: target.getBoundingClientRect() } as ResizeObserverEntry],
        this as unknown as ResizeObserver,
      )
    }
    unobserve() {}
    disconnect() {}
  }
})

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

  it('labels the Y axis with percentage values and the X axis with the sequence index, visible without hovering (FR-010)', () => {
    render(<ScoreBlock score={65} band="healthy" trend={[40, 50, 65]} onClick={() => {}} />)

    const yTicks = screen.getAllByText(/%$/)
    expect(yTicks.length).toBeGreaterThan(0)

    const xTicks = screen.getAllByText(/^[0-9]+$/)
    expect(xTicks.length).toBeGreaterThan(0)
  })

  it('renders the score at a large, prominent size (FR-009)', () => {
    render(<ScoreBlock score={65} band="at_risk" trend={[40, 50, 65]} onClick={() => {}} />)

    const scoreEl = screen.getByTestId('score-value')
    expect(scoreEl.className).toMatch(/text-(5|6|7)xl/)
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

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AuraRiskOrb } from './aura-risk-orb'

describe('AuraRiskOrb', () => {
  it('renders the given score', () => {
    render(<AuraRiskOrb score={65} band="at_risk" />)

    expect(screen.getByText('65')).toBeInTheDocument()
  })

  it('rounds a fractional score for display', () => {
    render(<AuraRiskOrb score={65.6} band="at_risk" />)

    expect(screen.getByText('66')).toBeInTheDocument()
  })

  it.each([
    ['healthy', '#a3a3a3'],
    ['watch', '#f59e0b'],
    ['at_risk', '#ef4444'],
  ] as const)('colors the orb from BAND_CHART_COLOR for band %s', (band, color) => {
    render(<AuraRiskOrb score={40} band={band} />)

    const orb = screen.getByTestId('aura-risk-orb')
    expect(orb.style.getPropertyValue('--orb-color')).toBe(color)
  })

  it('changes color across different bands', () => {
    const { rerender } = render(<AuraRiskOrb score={40} band="healthy" />)
    const healthyColor = screen.getByTestId('aura-risk-orb').style.getPropertyValue('--orb-color')

    rerender(<AuraRiskOrb score={90} band="at_risk" />)
    const atRiskColor = screen.getByTestId('aura-risk-orb').style.getPropertyValue('--orb-color')

    expect(healthyColor).not.toBe(atRiskColor)
  })
})

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { AuraRiskOrb } from './aura-risk-orb'

describe('AuraRiskOrb', () => {
  it.each([
    ['healthy', '#a3a3a3'],
    ['watch', '#f59e0b'],
    ['at_risk', '#ef4444'],
  ] as const)('colors the orb from BAND_CHART_COLOR for band %s', (band, color) => {
    render(<AuraRiskOrb band={band} />)

    const orb = screen.getByTestId('aura-risk-orb')
    expect(orb.style.getPropertyValue('--orb-color')).toBe(color)
  })

  it('changes color across different bands', () => {
    const { rerender } = render(<AuraRiskOrb band="healthy" />)
    const healthyColor = screen.getByTestId('aura-risk-orb').style.getPropertyValue('--orb-color')

    rerender(<AuraRiskOrb band="at_risk" />)
    const atRiskColor = screen.getByTestId('aura-risk-orb').style.getPropertyValue('--orb-color')

    expect(healthyColor).not.toBe(atRiskColor)
  })

  it('animates a continuous pulse regardless of band', () => {
    render(<AuraRiskOrb band="watch" />)

    expect(screen.getByTestId('aura-risk-orb').className).toContain('animate-aura-pulse')
  })

  it('does not render the numeric score', () => {
    render(<AuraRiskOrb band="at_risk" />)

    expect(screen.queryByText(/^\d+$/)).not.toBeInTheDocument()
  })
})

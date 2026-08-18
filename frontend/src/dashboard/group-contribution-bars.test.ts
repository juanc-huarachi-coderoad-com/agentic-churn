import { describe, expect, it } from 'vitest'
import { groupContributionBars } from './group-contribution-bars'
import type { ContributionBar } from './types'

function bar(overrides: Partial<ContributionBar> & Pick<ContributionBar, 'score_contribution_id'>): ContributionBar {
  return {
    label: 'escalation_language',
    points: 10,
    is_positive: false,
    ...overrides,
  }
}

describe('groupContributionBars', () => {
  it('sums same-label findings into one group and keeps every contribution id', () => {
    const bars = [
      bar({ score_contribution_id: 'a', label: 'escalation_language', points: 16, is_positive: false }),
      bar({ score_contribution_id: 'b', label: 'escalation_language', points: 19, is_positive: false }),
    ]

    const groups = groupContributionBars(bars)

    expect(groups).toHaveLength(1)
    expect(groups[0].label).toBe('escalation_language')
    expect(groups[0].points).toBe(35)
    expect(groups[0].is_positive).toBe(false)
    expect(groups[0].contribution_ids).toEqual(['a', 'b'])
  })

  it('passes through a label that appears once as a group of one', () => {
    const bars = [bar({ score_contribution_id: 'a', label: 'contact_absence', points: 8, is_positive: false })]

    const groups = groupContributionBars(bars)

    expect(groups).toHaveLength(1)
    expect(groups[0].contribution_ids).toEqual(['a'])
    expect(groups[0].points).toBe(8)
  })

  it('nets out positive (risk-reducing) findings using the same signed-points formula the UI displays', () => {
    const bars = [
      bar({ score_contribution_id: 'a', label: 'commitment_met', points: 7, is_positive: true }),
      bar({ score_contribution_id: 'b', label: 'commitment_met', points: 8, is_positive: true }),
    ]

    const groups = groupContributionBars(bars)

    expect(groups[0].points).toBe(-15)
    expect(groups[0].is_positive).toBe(true)
  })

  it('sorts groups by absolute net points descending', () => {
    const bars = [
      bar({ score_contribution_id: 'a', label: 'relationship_change', points: 3, is_positive: false }),
      bar({ score_contribution_id: 'b', label: 'broken_response_promise', points: 29, is_positive: false }),
      bar({ score_contribution_id: 'c', label: 'contact_absence', points: 8, is_positive: false }),
    ]

    const groups = groupContributionBars(bars)

    expect(groups.map((g) => g.label)).toEqual([
      'broken_response_promise',
      'contact_absence',
      'relationship_change',
    ])
  })
})

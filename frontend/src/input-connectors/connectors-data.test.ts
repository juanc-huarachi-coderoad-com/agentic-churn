import { describe, expect, it } from 'vitest'
import { CONNECTOR_GROUPS, CONNECTORS } from './connectors-data'

describe('CONNECTORS catalog', () => {
  it('matches the fixed table: 1 live, 6 simulated, 7 planned (spec FR-003–FR-005)', () => {
    expect(CONNECTORS.filter((c) => c.status === 'live')).toHaveLength(1)
    expect(CONNECTORS.filter((c) => c.status === 'simulated')).toHaveLength(6)
    expect(CONNECTORS.filter((c) => c.status === 'planned')).toHaveLength(7)
    expect(CONNECTORS).toHaveLength(14)
  })

  it('has a unique id for every connector', () => {
    const ids = CONNECTORS.map((c) => c.id)
    expect(new Set(ids).size).toBe(ids.length)
  })

  it('only the live connector carries a pipeline', () => {
    for (const connector of CONNECTORS) {
      if (connector.status === 'live') {
        expect(connector.pipeline).toBeDefined()
        expect(connector.pipeline?.length).toBeGreaterThan(0)
      } else {
        expect(connector.pipeline).toBeUndefined()
      }
    }
  })

  it('every connector has a non-empty description (spec SC-003)', () => {
    for (const connector of CONNECTORS) {
      expect(connector.description.trim().length).toBeGreaterThan(0)
    }
  })

  it("every brand icon's asset matches one of the downloaded files (research.md Decision 1)", () => {
    const downloadedAssets = new Set(['gmail.svg', 'zendesk.svg', 'jira.svg', 'intercom.svg'])
    for (const connector of CONNECTORS) {
      if (connector.icon.kind === 'brand') {
        expect(downloadedAssets.has(connector.icon.asset)).toBe(true)
      }
    }
  })
})

describe('CONNECTOR_GROUPS', () => {
  it("derives each group's count from its own connectors array, never a hand-typed number", () => {
    for (const group of CONNECTOR_GROUPS) {
      const expected = CONNECTORS.filter((c) => c.status === group.status).length
      expect(group.connectors).toHaveLength(expected)
    }
  })

  it('orders groups Live, Simulated, Planned to match the reference mockup', () => {
    expect(CONNECTOR_GROUPS.map((g) => g.status)).toEqual(['live', 'simulated', 'planned'])
  })
})

import { describe, expect, it } from 'vitest'
import { TYPE_ICON, TYPE_LABEL } from './signal-type'
import type { SignalType } from './types'

const ALL_SIGNAL_TYPES: SignalType[] = [
  'message',
  'ticket_state_change',
  'usage_measurement',
  'survey_response',
  'meeting',
  'absence',
  'crm_change',
]

describe('signal-type', () => {
  it('has exactly the 7 SignalType keys in TYPE_LABEL, each with a label', () => {
    expect(Object.keys(TYPE_LABEL).sort()).toEqual([...ALL_SIGNAL_TYPES].sort())
    for (const type of ALL_SIGNAL_TYPES) {
      expect(TYPE_LABEL[type]).toBeTruthy()
    }
  })

  it('has exactly the 7 SignalType keys in TYPE_ICON, each with a distinct icon', () => {
    expect(Object.keys(TYPE_ICON).sort()).toEqual([...ALL_SIGNAL_TYPES].sort())
    const icons = ALL_SIGNAL_TYPES.map((type) => TYPE_ICON[type])
    expect(new Set(icons).size).toBe(ALL_SIGNAL_TYPES.length)
  })

  it('gives every SignalType a distinct display label', () => {
    const labels = ALL_SIGNAL_TYPES.map((type) => TYPE_LABEL[type])
    expect(new Set(labels).size).toBe(ALL_SIGNAL_TYPES.length)
  })
})

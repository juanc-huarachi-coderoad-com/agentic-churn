import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CONNECTORS } from './connectors-data'
import { ConnectorCard } from './connector-card'

function findConnector(id: string) {
  const connector = CONNECTORS.find((c) => c.id === id)
  if (!connector) throw new Error(`fixture connector "${id}" not found`)
  return connector
}

describe('ConnectorCard', () => {
  it('renders name, icon, description, and status badge for a live connector', () => {
    render(<ConnectorCard connector={findConnector('transcripts')} variant="row" />)

    expect(screen.getByText('Transcripts')).toBeInTheDocument()
    expect(screen.getByText('Meeting audio')).toBeInTheDocument()
    expect(screen.getByText('Live')).toBeInTheDocument()
  })

  it('renders name, icon, description, and status badge for a simulated connector', () => {
    render(<ConnectorCard connector={findConnector('gmail')} />)

    expect(screen.getByText('Gmail')).toBeInTheDocument()
    expect(screen.getByRole('img', { name: 'Gmail logo' })).toBeInTheDocument()
    expect(screen.getByText('Email threads and client conversations')).toBeInTheDocument()
    expect(screen.getByText('Simulated')).toBeInTheDocument()
  })

  it('renders name, icon, description, and status badge for a planned connector', () => {
    render(<ConnectorCard connector={findConnector('teams')} />)

    expect(screen.getByText('Teams')).toBeInTheDocument()
    expect(screen.getByText('Microsoft Teams chat and meetings')).toBeInTheDocument()
    expect(screen.getByText('Planned')).toBeInTheDocument()
  })

  it("renders the Transcripts entry's pipeline alongside its description (spec FR-003)", () => {
    render(<ConnectorCard connector={findConnector('transcripts')} variant="row" />)

    expect(screen.getByText('Meeting audio')).toBeInTheDocument()
    expect(
      screen.getByText('(local storage + OpenAI Whisper + pyannote.ai + Anthropic)'),
    ).toBeInTheDocument()
  })

  it('does not render a pipeline line for connectors that have none', () => {
    render(<ConnectorCard connector={findConnector('gmail')} />)

    expect(screen.queryByText(/OpenAI Whisper/)).not.toBeInTheDocument()
  })
})

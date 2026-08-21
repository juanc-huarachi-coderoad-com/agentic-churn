import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { CONNECTORS } from './connectors-data'
import { InputConnectorsPage } from './input-connectors-page'

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/connectors']}>
      <InputConnectorsPage />
    </MemoryRouter>,
  )
}

describe('InputConnectorsPage', () => {
  it('renders three group headings with counts matching the fixed catalog (spec Acceptance Scenario 1-2)', () => {
    renderPage()

    expect(screen.getByText('Live (1)')).toBeInTheDocument()
    expect(screen.getByText('Simulated (6)')).toBeInTheDocument()
    expect(screen.getByText('Planned (7)')).toBeInTheDocument()
  })

  it('renders every connector from the catalog exactly once', () => {
    renderPage()

    for (const connector of CONNECTORS) {
      expect(screen.getByText(connector.name)).toBeInTheDocument()
    }
  })

  it('shows all three group headings without any scrolling container hiding them (SC-001)', () => {
    renderPage()

    expect(screen.getByText('Live (1)')).toBeVisible()
    expect(screen.getByText('Simulated (6)')).toBeVisible()
    expect(screen.getByText('Planned (7)')).toBeVisible()
  })

  it('shows a clearly labeled "Add Connector" action (spec FR-007)', () => {
    renderPage()

    expect(screen.getByRole('button', { name: /add connector/i })).toBeInTheDocument()
  })
})

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { AppShell } from './app-shell'

function renderShell(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AppShell>
        <p>Page content</p>
      </AppShell>
    </MemoryRouter>,
  )
}

describe('AppShell', () => {
  it('renders the sidebar destinations alongside the page content', () => {
    renderShell('/coverage')

    expect(screen.getByRole('link', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Coverage' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Profile' })).toBeInTheDocument()
  })

  it('renders children inside the main content area', () => {
    renderShell('/coverage')

    expect(screen.getByRole('main')).toHaveTextContent('Page content')
  })

  it('renders the breadcrumb above the page content', () => {
    renderShell('/coverage')

    const main = screen.getByRole('main')
    const breadcrumb = screen.getByRole('navigation', { name: 'Breadcrumb' })
    const content = screen.getByText('Page content')

    expect(main).toContainElement(breadcrumb)
    expect(
      breadcrumb.compareDocumentPosition(content) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })

  it('renders the Live badge and notification bell alongside the breadcrumb', () => {
    renderShell('/coverage')

    const breadcrumb = screen.getByRole('navigation', { name: 'Breadcrumb' })
    const liveBadge = screen.getByText('Live')

    expect(breadcrumb.parentElement).toContainElement(liveBadge)
    expect(document.querySelector('.lucide-bell')).toBeInTheDocument()
  })
})

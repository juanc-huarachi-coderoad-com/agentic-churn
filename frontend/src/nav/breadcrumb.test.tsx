import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { Breadcrumb } from './breadcrumb'

function renderBreadcrumb(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Breadcrumb />
    </MemoryRouter>,
  )
}

describe('Breadcrumb', () => {
  it('shows Home > Coverage on the coverage screen, with Home linking to /dashboard', () => {
    renderBreadcrumb('/coverage')

    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/dashboard')
    expect(screen.getByText('Coverage')).toBeInTheDocument()
  })

  it('shows Home > Input Connectors on the connectors screen', () => {
    renderBreadcrumb('/connectors')

    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/dashboard')
    expect(screen.getByText('Input Connectors')).toBeInTheDocument()
  })

  it('shows Home > Profile on the profile screen', () => {
    renderBreadcrumb('/profile')

    expect(screen.getByRole('link', { name: 'Home' })).toHaveAttribute('href', '/dashboard')
    expect(screen.getByText('Profile')).toBeInTheDocument()
  })

  it('shows only a non-clickable "Home" label on the dashboard (home) screen', () => {
    renderBreadcrumb('/dashboard')

    expect(screen.queryByRole('link', { name: 'Home' })).not.toBeInTheDocument()
    expect(screen.getByText('Home')).toBeInTheDocument()
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
  })
})

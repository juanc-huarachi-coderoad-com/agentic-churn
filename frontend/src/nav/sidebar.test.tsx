import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'
import { Sidebar } from './sidebar'

function renderSidebar(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Sidebar />
    </MemoryRouter>,
  )
}

describe('Sidebar', () => {
  it('renders exactly one link per existing destination — Dashboard, Coverage, Profile', () => {
    renderSidebar('/dashboard')

    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('href', '/dashboard')
    expect(screen.getByRole('link', { name: 'Coverage' })).toHaveAttribute('href', '/coverage')
    expect(screen.getByRole('link', { name: 'Profile' })).toHaveAttribute('href', '/profile')
    expect(screen.getAllByRole('link')).toHaveLength(3)
  })

  it('marks the current route as active and no other route', () => {
    renderSidebar('/dashboard')

    expect(screen.getByRole('link', { name: 'Dashboard' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Coverage' })).not.toHaveAttribute('aria-current')
    expect(screen.getByRole('link', { name: 'Profile' })).not.toHaveAttribute('aria-current')
  })

  it('marks Coverage as active when on the coverage route', () => {
    renderSidebar('/coverage')

    expect(screen.getByRole('link', { name: 'Coverage' })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: 'Dashboard' })).not.toHaveAttribute('aria-current')
  })

  it('renders the account menu trigger after the three destination links', () => {
    renderSidebar('/dashboard')

    expect(screen.getByRole('button', { name: /account/i })).toBeInTheDocument()
  })

  it('shows a tooltip naming the destination on hover', async () => {
    renderSidebar('/dashboard')

    await userEvent.hover(screen.getByRole('link', { name: 'Coverage' }))

    expect(await screen.findByRole('tooltip')).toHaveTextContent('Coverage')
  })

  it('shows the same tooltip on keyboard focus, not hover-only', async () => {
    renderSidebar('/dashboard')

    screen.getByRole('link', { name: 'Profile' }).focus()

    expect(await screen.findByRole('tooltip')).toHaveTextContent('Profile')
  })

  it('marks the active link with more than just a color change', async () => {
    renderSidebar('/dashboard')

    await waitFor(() => {
      expect(
        screen.getByRole('link', { name: 'Dashboard' }).querySelector('[data-active-indicator]'),
      ).not.toBeNull()
    })
    expect(
      screen.getByRole('link', { name: 'Coverage' }).querySelector('[data-active-indicator]'),
    ).toBeNull()
  })
})

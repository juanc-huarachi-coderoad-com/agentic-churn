import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { AccountMenu } from './account-menu'

const logoutMock = vi.fn()
vi.mock('../auth/use-logout', () => ({
  useLogout: () => logoutMock,
}))

describe('AccountMenu', () => {
  it('opens a menu containing exactly one item, "Log out"', async () => {
    render(<AccountMenu />)

    await userEvent.click(screen.getByRole('button', { name: /account/i }))

    const items = await screen.findAllByRole('menuitem')
    expect(items).toHaveLength(1)
    expect(items[0]).toHaveTextContent('Log out')
  })

  it('closes without logging out when Escape is pressed', async () => {
    render(<AccountMenu />)

    await userEvent.click(screen.getByRole('button', { name: /account/i }))
    expect(await screen.findByRole('menuitem')).toBeInTheDocument()

    await userEvent.keyboard('{Escape}')

    expect(screen.queryByRole('menuitem')).not.toBeInTheDocument()
    expect(logoutMock).not.toHaveBeenCalled()
  })

  it('invokes the logout action when "Log out" is clicked', async () => {
    render(<AccountMenu />)

    await userEvent.click(screen.getByRole('button', { name: /account/i }))
    await userEvent.click(await screen.findByRole('menuitem', { name: 'Log out' }))

    expect(logoutMock).toHaveBeenCalledTimes(1)
  })
})

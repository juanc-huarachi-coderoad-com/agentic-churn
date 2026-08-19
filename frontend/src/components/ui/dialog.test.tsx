import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Dialog, DialogClose, DialogContent, DialogOverlay } from './dialog'

function renderDialog(onOpenChange = vi.fn()) {
  return render(
    <Dialog open onOpenChange={onOpenChange}>
      <DialogOverlay />
      <DialogContent aria-label="Test dialog">
        <p>Dialog body content</p>
        <button type="button">Inside button one</button>
        <DialogClose asChild>
          <button type="button">Close</button>
        </DialogClose>
      </DialogContent>
    </Dialog>,
  )
}

describe('Dialog', () => {
  it('renders centered content over a backdrop when open', () => {
    renderDialog()

    expect(screen.getByRole('dialog', { name: 'Test dialog' })).toBeInTheDocument()
    expect(screen.getByText('Dialog body content')).toBeInTheDocument()
  })

  it('renders nothing when closed', () => {
    render(
      <Dialog open={false} onOpenChange={vi.fn()}>
        <DialogOverlay />
        <DialogContent aria-label="Test dialog">
          <p>Dialog body content</p>
        </DialogContent>
      </Dialog>,
    )

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('calls onOpenChange(false) on Escape', async () => {
    const onOpenChange = vi.fn()
    renderDialog(onOpenChange)

    await userEvent.keyboard('{Escape}')

    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false))
  })

  it('calls onOpenChange(false) on backdrop click', async () => {
    const onOpenChange = vi.fn()
    renderDialog(onOpenChange)

    await userEvent.click(screen.getByTestId('dialog-overlay'))

    await waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false))
  })

  it('traps focus within the content while open', async () => {
    renderDialog()

    // Radix moves initial focus into the content on open.
    await waitFor(() => {
      const dialog = screen.getByRole('dialog')
      expect(dialog.contains(document.activeElement)).toBe(true)
    })
  })

  it('closes via an explicit DialogClose control', async () => {
    const onOpenChange = vi.fn()
    renderDialog(onOpenChange)

    await userEvent.click(screen.getByRole('button', { name: 'Close' }))

    expect(onOpenChange).toHaveBeenCalledWith(false)
  })
})

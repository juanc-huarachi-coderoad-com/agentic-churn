import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MarkdownText } from './markdown-text'

describe('MarkdownText', () => {
  it('renders headings, emphasis, and lists', () => {
    render(<MarkdownText markdown={'## Heading\n\n**bold** text and a list:\n\n- one\n- two'} />)

    expect(screen.getByRole('heading', { name: 'Heading' })).toBeInTheDocument()
    expect(screen.getByText('bold').tagName).toBe('STRONG')
    expect(screen.getByText('one')).toBeInTheDocument()
    expect(screen.getByText('two')).toBeInTheDocument()
  })

  it('renders fenced code blocks in a distinguishable, non-reflowed format', () => {
    render(<MarkdownText markdown={'```\nconst x = 1;\n```'} />)

    const code = screen.getByText('const x = 1;')
    expect(code.tagName).toBe('CODE')
    expect(code.closest('pre')).toBeInTheDocument()
  })

  // FR-007, research.md Decision 7 — react-markdown never renders raw
  // embedded HTML by default (no rehype-raw plugin). Content that looks
  // like an HTML tag (e.g. quoted from a client message containing
  // something instruction-shaped) must render as inert literal text, never
  // as an executable/interactive element.
  it('never renders embedded HTML — it renders as inert literal text', () => {
    render(<MarkdownText markdown={'The client wrote: <img src=x onerror="window.hacked=true">'} />)

    expect(document.querySelector('img')).not.toBeInTheDocument()
    expect((window as unknown as { hacked?: boolean }).hacked).toBeUndefined()
    expect(screen.getByText(/img src=x onerror/)).toBeInTheDocument()
  })

  it('never renders an embedded script tag', () => {
    render(<MarkdownText markdown={'<script>window.hacked = true</script>'} />)

    expect(document.querySelector('script')).not.toBeInTheDocument()
    expect((window as unknown as { hacked?: boolean }).hacked).toBeUndefined()
  })
})

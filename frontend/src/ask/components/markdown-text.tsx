import ReactMarkdown from 'react-markdown'

interface MarkdownTextProps {
  markdown: string
}

// specs/014-ask-agent-response-formats, research.md Decisions 7-8 —
// react-markdown compiles Markdown directly to React elements and never
// renders raw embedded HTML by default (no rehype-raw/rehype-sanitize
// plugin installed here) — a structural prompt-injection defense at the
// rendering layer: any client-message content that made it into generated
// Markdown, even something shaped like an HTML tag, renders as inert
// literal text, never executed (FR-007). Code blocks use the default
// monospace, non-reflowed <pre><code> output — no syntax-highlighting
// dependency, per Decision 8.
export function MarkdownText({ markdown }: MarkdownTextProps) {
  return (
    <div className="ask-markdown text-sm text-neutral-800">
      <ReactMarkdown
        components={{
          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
          h1: ({ children }) => <h1 className="mb-2 text-base font-semibold">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-2 text-base font-semibold">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-2 text-sm font-semibold">{children}</h3>,
          ul: ({ children }) => <ul className="mb-2 list-disc space-y-1 pl-5">{children}</ul>,
          ol: ({ children }) => <ol className="mb-2 list-decimal space-y-1 pl-5">{children}</ol>,
          code: ({ children }) => (
            <code className="rounded bg-neutral-100 px-1 py-0.5 font-mono text-xs">{children}</code>
          ),
          pre: ({ children }) => (
            <pre className="mb-2 overflow-x-auto rounded-md bg-neutral-100 p-3 font-mono text-xs">
              {children}
            </pre>
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  )
}

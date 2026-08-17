import type { CoverageLine as CoverageLineData } from './types'

interface CoverageLineProps {
  coverage: CoverageLineData
}

export function CoverageLine({ coverage }: CoverageLineProps) {
  const completeTo = coverage.complete_to
    ? new Date(coverage.complete_to).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : '—'

  return (
    <p className="mt-6 border-t border-neutral-100 pt-4 text-xs text-neutral-400">
      Reading {coverage.sources_read} of {coverage.sources_expected} sources · complete to{' '}
      {completeTo}
    </p>
  )
}

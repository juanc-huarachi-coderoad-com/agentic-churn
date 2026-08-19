// Mirrors contracts/coverage.md's CoverageResponse (architecture/07-api-spec.md).

export interface SourceStatus {
  source_type: string
  status: 'connected' | 'degraded' | 'disconnected'
  last_successful_sync_at: string | null
}

export interface QuarantineEntry {
  finding_id: string
  failed_check: string
}

export interface CoverageResponse {
  sources: SourceStatus[]
  quarantine: QuarantineEntry[]
}

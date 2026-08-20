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

// Mirrors contracts/meeting-audio.md's consent endpoints
// (specs/019-meeting-audio-ingestion).
export interface ConsentEntry {
  series_id: string
  status: 'granted' | 'revoked'
  all_parties_confirmed: boolean
  documented_by: string
  documented_at: string
  note: string | null
}

export interface ConsentListResponse {
  series: ConsentEntry[]
}

export interface ConsentRequest {
  series_id: string
  status: 'granted' | 'revoked'
  all_parties_confirmed: boolean
  note?: string | null
}

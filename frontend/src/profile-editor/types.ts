// Mirrors backend/app/context/adapters/profile_router.py's `ProfileResponse`
// (architecture/07-api-spec.md, GET /api/profile) — the read-side shape, distinct
// from ProfileFormValues (schema.ts), which mirrors the write-side ClientProfileInput.
export interface StakeholderResponse {
  name: string
  role: string | null
  influence: string
  signs_renewal: boolean
}

export interface ProductAreaResponse {
  key: string
  criticality: string
}

export interface CommitmentResponse {
  type: string
  threshold_business_hours: number | null
}

export interface ProfileResponse {
  version_number: number
  client_name: string
  renewal_date: string
  contract_value_band: string
  stakeholders: StakeholderResponse[]
  product_areas: ProductAreaResponse[]
  commitments: CommitmentResponse[]
  exclusions: string[]
  communication_norms: string | null
}

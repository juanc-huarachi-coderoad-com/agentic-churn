// Mirrors backend/app/context/domain/profile_schema.py's `ClientProfileInput`
// exactly — the same Pydantic model both the YAML-file path and this feature's
// `POST /api/profile` route validate against (specs/011-production-hardening,
// research.md Decision 4). Client-side validation here is UX only; the backend
// re-validates independently (constitution Full-Stack §5 "Zero Trust Validation").
//
// Deliberately no `.default()` anywhere below: Zod's `.default()` makes a
// field's *input* type optional while its *output* type stays required, which
// react-hook-form's `useForm<T>` can't reconcile (it needs one type for both).
// `profile-editor-form.tsx`'s `toFormValues()` already populates every field
// explicitly on load, so no schema-level default is needed here at all.
import { z } from 'zod'

const INFLUENCE_LEVELS = ['sponsor', 'daily_user', 'unknown'] as const
const CRITICALITY_LEVELS = ['critical', 'standard', 'peripheral'] as const
const CONTRACT_VALUE_BANDS = ['strategic', 'standard', 'smb'] as const

export const stakeholderSchema = z.object({
  id: z.string().min(1, 'Required'),
  name: z.string().min(1, 'Required'),
  role: z.string().nullable().optional(),
  influence: z.enum(INFLUENCE_LEVELS),
  signs_renewal: z.boolean(),
  identifiers: z.array(z.string()),
})

const productAreaSchema = z.object({
  key: z.string().min(1, 'Required'),
  criticality: z.enum(CRITICALITY_LEVELS),
})

const commitmentSchema = z.object({
  type: z.string().min(1, 'Required'),
  priority: z.string().nullable().optional(),
  threshold_business_hours: z.number().nullable().optional(),
  cadence: z.string().nullable().optional(),
})

const communicationSchema = z.object({
  working_hours: z.string().regex(/^\d{2}:\d{2}-\d{2}:\d{2}$/, 'Must look like "08:00-18:00"'),
  timezone: z.string().min(1, 'Required'),
  languages: z.array(z.string()),
  norms: z.string().nullable().optional(),
})

export const profileSchema = z
  .object({
    client: z.string().min(1, 'Required'),
    renewal_date: z.string().min(1, 'Required'), // "YYYY-MM-DD"
    contract_value_band: z.enum(CONTRACT_VALUE_BANDS),
    business_goals: z.array(z.string()),
    stakeholders: z.array(stakeholderSchema).min(1, 'At least one stakeholder is required'),
    product_areas: z.array(productAreaSchema),
    commitments: z.array(commitmentSchema),
    communication: communicationSchema,
    exclusions: z.array(z.string()),
    history: z.array(z.object({ date: z.string(), event: z.string() })),
  })
  .refine((profile) => profile.stakeholders.some((s) => s.signs_renewal), {
    message: 'At least one stakeholder must have "signs renewal" checked',
    path: ['stakeholders'],
  })

export type ProfileFormValues = z.infer<typeof profileSchema>

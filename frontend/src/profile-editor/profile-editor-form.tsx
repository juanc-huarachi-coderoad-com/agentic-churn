import { zodResolver } from '@hookform/resolvers/zod'
import { useEffect } from 'react'
import { Controller, useFieldArray, useForm } from 'react-hook-form'
import { type ProfileFormValues, profileSchema } from './schema'
import type { ProfileResponse } from './types'
import { useProfile, useSubmitProfile } from './use-profile'

// FR-017 scopes this editor to stakeholders/exclusions/renewal date/contract
// value band/communication norms — GET /api/profile (ProfileResponse) doesn't
// carry business_goals, full commitment detail beyond type/threshold, product
// area criticality's own multiplier, working_hours/timezone/languages, or
// history, so those fields aren't editable here and are resubmitted with
// these fixed defaults on every save (a known, deliberate limitation, not a
// silent data-loss bug — see this file's own comment at the submit handler).
const UNEDITED_DEFAULTS = {
  business_goals: [] as string[],
  working_hours: '08:00-18:00',
  timezone: 'America/Bogota',
  languages: ['es', 'en'],
  history: [] as { date: string; event: string }[],
}

function toFormValues(profile: ProfileResponse): ProfileFormValues {
  return {
    client: profile.client_name,
    renewal_date: profile.renewal_date,
    contract_value_band: profile.contract_value_band as ProfileFormValues['contract_value_band'],
    business_goals: UNEDITED_DEFAULTS.business_goals,
    stakeholders: profile.stakeholders.map((s, i) => ({
      id: `stk-${i}`,
      name: s.name,
      role: s.role,
      influence: s.influence as ProfileFormValues['stakeholders'][number]['influence'],
      signs_renewal: s.signs_renewal,
      identifiers: [],
    })),
    product_areas: profile.product_areas.map((a) => ({
      key: a.key,
      criticality: a.criticality as ProfileFormValues['product_areas'][number]['criticality'],
    })),
    commitments: profile.commitments.map((c) => ({
      type: c.type,
      threshold_business_hours: c.threshold_business_hours,
    })),
    communication: {
      working_hours: UNEDITED_DEFAULTS.working_hours,
      timezone: UNEDITED_DEFAULTS.timezone,
      languages: UNEDITED_DEFAULTS.languages,
      norms: profile.communication_norms,
    },
    exclusions: profile.exclusions,
    history: UNEDITED_DEFAULTS.history,
  }
}

// Empty-but-well-typed defaults — `useForm()` runs on the very first render,
// before `useProfile()`'s data (and this component's own `reset()` effect)
// exist, so every array field needs a real `[]` here, not `undefined`, or the
// exclusions/stakeholder `Controller`/`useFieldArray` bindings below throw on
// that first render (a real crash caught by this file's own tests, not by
// inspection).
const EMPTY_DEFAULTS: ProfileFormValues = {
  client: '',
  renewal_date: '',
  contract_value_band: 'standard',
  business_goals: [],
  stakeholders: [],
  product_areas: [],
  commitments: [],
  communication: { working_hours: '08:00-18:00', timezone: 'UTC', languages: [], norms: null },
  exclusions: [],
  history: [],
}

export function ProfileEditorForm() {
  const { data: profile, isLoading, isError } = useProfile()
  const submitProfile = useSubmitProfile()
  const {
    register,
    handleSubmit,
    reset,
    control,
    setError,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: EMPTY_DEFAULTS,
  })

  const stakeholderFields = useFieldArray({ control, name: 'stakeholders' })

  useEffect(() => {
    if (profile) {
      reset(toFormValues(profile))
    }
  }, [profile, reset])

  if (isLoading) {
    return <p className="p-8 text-sm text-neutral-500">Loading…</p>
  }
  if (isError || !profile) {
    return <p className="p-8 text-sm text-red-600">Couldn't load the client profile.</p>
  }

  const onSubmit = async (values: ProfileFormValues) => {
    try {
      await submitProfile.mutateAsync(values)
    } catch (error) {
      const detail = (error as { detail?: unknown }).detail
      setError('root', {
        message:
          typeof detail === 'string' || Array.isArray(detail)
            ? JSON.stringify(detail)
            : 'Could not save the profile — check the fields above.',
      })
    }
  }

  return (
    <main className="mx-auto max-w-2xl p-8">
      <h1 className="text-lg font-medium text-neutral-900">Client profile</h1>
      <p className="mt-1 text-sm text-neutral-500">Version {profile.version_number}</p>

      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="mt-6 space-y-6">
        <div>
          <label htmlFor="client" className="block text-sm text-neutral-600">
            Client name
          </label>
          <input
            id="client"
            className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
            {...register('client')}
          />
          {errors.client && <p className="mt-1 text-sm text-red-600">{errors.client.message}</p>}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="renewal_date" className="block text-sm text-neutral-600">
              Renewal date
            </label>
            <input
              id="renewal_date"
              type="date"
              className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
              {...register('renewal_date')}
            />
            {errors.renewal_date && (
              <p className="mt-1 text-sm text-red-600">{errors.renewal_date.message}</p>
            )}
          </div>
          <div>
            <label htmlFor="contract_value_band" className="block text-sm text-neutral-600">
              Contract value band
            </label>
            <select
              id="contract_value_band"
              className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
              {...register('contract_value_band')}
            >
              <option value="strategic">Strategic</option>
              <option value="standard">Standard</option>
              <option value="smb">SMB</option>
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="communication.norms" className="block text-sm text-neutral-600">
            Communication norms
          </label>
          <textarea
            id="communication.norms"
            rows={3}
            className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
            {...register('communication.norms')}
          />
        </div>

        <div>
          <label htmlFor="exclusions" className="block text-sm text-neutral-600">
            Exclusions (comma-separated)
          </label>
          <Controller
            control={control}
            name="exclusions"
            render={({ field }) => (
              <input
                id="exclusions"
                className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
                value={field.value.join(', ')}
                onChange={(e) =>
                  field.onChange(
                    e.target.value
                      .split(',')
                      .map((v) => v.trim())
                      .filter(Boolean),
                  )
                }
              />
            )}
          />
        </div>

        <div>
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-neutral-900">Stakeholders</h2>
            <button
              type="button"
              onClick={() =>
                stakeholderFields.append({
                  id: `stk-new-${stakeholderFields.fields.length}`,
                  name: '',
                  role: null,
                  influence: 'unknown',
                  signs_renewal: false,
                  identifiers: [],
                })
              }
              className="text-sm text-neutral-600 underline"
            >
              + Add stakeholder
            </button>
          </div>

          <div className="mt-2 space-y-3">
            {stakeholderFields.fields.map((field, index) => (
              <div key={field.id} className="grid grid-cols-12 items-center gap-2">
                <input
                  className="col-span-4 rounded border border-neutral-300 px-2 py-1 text-sm"
                  placeholder="Name"
                  {...register(`stakeholders.${index}.name`)}
                />
                <input
                  className="col-span-3 rounded border border-neutral-300 px-2 py-1 text-sm"
                  placeholder="Role"
                  {...register(`stakeholders.${index}.role`)}
                />
                <select
                  className="col-span-3 rounded border border-neutral-300 px-2 py-1 text-sm"
                  {...register(`stakeholders.${index}.influence`)}
                >
                  <option value="sponsor">Sponsor</option>
                  <option value="daily_user">Daily user</option>
                  <option value="unknown">Unknown</option>
                </select>
                <label className="col-span-1 flex items-center gap-1 text-xs text-neutral-600">
                  <input type="checkbox" {...register(`stakeholders.${index}.signs_renewal`)} />
                  Signs
                </label>
                <button
                  type="button"
                  onClick={() => stakeholderFields.remove(index)}
                  className="col-span-1 text-xs text-red-600"
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
          {errors.stakeholders && (
            <p className="mt-1 text-sm text-red-600">
              {errors.stakeholders.message ?? errors.stakeholders.root?.message}
            </p>
          )}
        </div>

        {errors.root && <p className="text-sm text-red-600">{errors.root.message}</p>}

        <button
          type="submit"
          disabled={isSubmitting || !isDirty}
          className="rounded bg-neutral-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          {isSubmitting ? 'Saving…' : 'Save changes'}
        </button>
      </form>
    </main>
  )
}

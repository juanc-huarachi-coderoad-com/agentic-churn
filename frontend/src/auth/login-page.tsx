import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router'
import { z } from 'zod'
import { apiFetch } from './api-client'
import { useAuthStore } from './auth-store'

// Client-side validation is UX only — the backend re-validates independently
// (constitution Full-Stack §5 "Zero Trust Validation"); this schema just gives the CS
// lead a fast, specific error before a round-trip.
const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
})

type LoginFormValues = z.infer<typeof loginSchema>

interface LoginResponse {
  token: string
  expires_at: string
}

export function LoginPage() {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (values: LoginFormValues) => {
    const response = await apiFetch('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(values),
    })

    if (!response.ok) {
      // Deliberately the same message regardless of which case the backend hit
      // (REQ-AUTH-08 applied through to the UI, not just the API response body).
      setError('root', { message: 'Invalid username or password.' })
      return
    }

    const data = (await response.json()) as LoginResponse
    login(data.token)
    void navigate('/dashboard')
  }

  return (
    <main className="flex min-h-svh items-center justify-center">
      <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="w-full max-w-sm space-y-4 p-8">
        <h1 className="text-lg font-medium text-neutral-900">Log in</h1>

        <div>
          <label htmlFor="username" className="block text-sm text-neutral-600">
            Username
          </label>
          <input
            id="username"
            autoComplete="username"
            className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
            {...register('username')}
          />
          {errors.username && <p className="mt-1 text-sm text-red-600">{errors.username.message}</p>}
        </div>

        <div>
          <label htmlFor="password" className="block text-sm text-neutral-600">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            className="mt-1 w-full rounded border border-neutral-300 px-3 py-2"
            {...register('password')}
          />
          {errors.password && <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>}
        </div>

        {errors.root && <p className="text-sm text-red-600">{errors.root.message}</p>}

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full rounded bg-neutral-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {isSubmitting ? 'Logging in…' : 'Log in'}
        </button>
      </form>
    </main>
  )
}

import { zodResolver } from '@hookform/resolvers/zod'
import { Eye, EyeOff, Lock, TriangleAlert, User } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router'
import { z } from 'zod'
import { Button } from '../components/ui/button'
import { Icon } from '../components/ui/icon'
import { cn } from '../lib/utils'
import { apiFetch } from './api-client'
import { useAuthStore } from './auth-store'
import { LoginBrandPanel } from './login-brand-panel'

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
  const [passwordVisible, setPasswordVisible] = useState(false)
  const {
    register,
    handleSubmit,
    setError,
    clearErrors,
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
    <main className="flex min-h-svh w-full bg-neutral-50">
      <LoginBrandPanel />

      <div className="flex flex-1 items-center justify-center p-8">
        <form onSubmit={(e) => void handleSubmit(onSubmit)(e)} className="w-full max-w-sm">
          <LoginBrandPanel compact />

          <h1 className="text-2xl font-semibold text-neutral-900">Welcome back</h1>
          <p className="mt-1.5 mb-8 text-sm text-neutral-500">Log in to your AURA workspace</p>

          {errors.root && (
            <div
              role="alert"
              className="mb-5 flex items-start gap-2 rounded-md bg-red-50 px-3 py-2.5 text-sm text-red-700"
            >
              <Icon icon={TriangleAlert} size={16} className="mt-0.5 shrink-0 text-red-600" />
              <span>{errors.root.message}</span>
            </div>
          )}

          <div className="mb-5">
            <label
              htmlFor="username"
              className="mb-1.5 block text-sm font-medium text-neutral-700"
            >
              Username
            </label>
            <div
              className={cn(
                'flex items-center rounded-md border border-neutral-300 bg-white transition-colors focus-within:border-neutral-400 focus-within:ring-[3px] focus-within:ring-neutral-900/8',
                errors.username && 'border-red-500 focus-within:ring-red-500/10',
              )}
            >
              <Icon icon={User} size={16} className="ml-3 shrink-0 text-neutral-400" />
              <input
                id="username"
                autoComplete="username"
                aria-invalid={!!errors.username}
                className="h-11 w-full min-w-0 bg-transparent px-3 text-sm text-neutral-900 outline-none"
                {...register('username', { onChange: () => clearErrors('root') })}
              />
            </div>
            {errors.username && (
              <p className="mt-1.5 text-sm text-red-600">{errors.username.message}</p>
            )}
          </div>

          <div className="mb-6">
            <label
              htmlFor="password"
              className="mb-1.5 block text-sm font-medium text-neutral-700"
            >
              Password
            </label>
            <div
              className={cn(
                'flex items-center rounded-md border border-neutral-300 bg-white transition-colors focus-within:border-neutral-400 focus-within:ring-[3px] focus-within:ring-neutral-900/8',
                errors.password && 'border-red-500 focus-within:ring-red-500/10',
              )}
            >
              <Icon icon={Lock} size={16} className="ml-3 shrink-0 text-neutral-400" />
              <input
                id="password"
                type={passwordVisible ? 'text' : 'password'}
                autoComplete="current-password"
                aria-invalid={!!errors.password}
                className="h-11 w-full min-w-0 bg-transparent px-3 text-sm text-neutral-900 outline-none"
                {...register('password', { onChange: () => clearErrors('root') })}
              />
              <button
                type="button"
                onClick={() => setPasswordVisible((visible) => !visible)}
                aria-label={passwordVisible ? 'Hide characters' : 'Reveal characters'}
                className="flex h-11 w-10 shrink-0 items-center justify-center text-neutral-400 transition-colors hover:text-neutral-600 focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-neutral-900"
              >
                <Icon icon={passwordVisible ? EyeOff : Eye} size={16} />
              </button>
            </div>
            {errors.password && (
              <p className="mt-1.5 text-sm text-red-600">{errors.password.message}</p>
            )}
          </div>

          <Button type="submit" disabled={isSubmitting} className="w-full">
            {isSubmitting ? 'Logging in…' : 'Log in'}
          </Button>
        </form>
      </div>
    </main>
  )
}

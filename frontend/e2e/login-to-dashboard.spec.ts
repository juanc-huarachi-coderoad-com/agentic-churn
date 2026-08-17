import { expect, test } from '@playwright/test'

// The full vertical slice spec.md names: real login issuing a real token, a dashboard
// screen rendering against seeded data through the real API, deployed end to end.
// Requires the backend running against a migrated + seeded database — see
// specs/002-dashboard-shell/quickstart.md §3.

test('an unauthenticated visitor is redirected to /login', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/login$/)
  await expect(page.getByRole('heading', { name: 'Log in' })).toBeVisible()
})

test('logging in with valid credentials reaches the dashboard shell', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Username').fill('marta')
  await page.getByLabel('Password').fill('agentic-demo-2026')
  await page.getByRole('button', { name: 'Log in' }).click()

  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Meridian Logistics' })).toBeVisible()
  // Asserts the dashboard shell rendered, not a specific account state —
  // the seeded account naturally progresses past "learning" over time
  // (specs/013-dashboard-reliability-fixes, research.md Decision 3).
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible()
})

test('an invalid login shows an error and stays on /login', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Username').fill('marta')
  await page.getByLabel('Password').fill('wrong-password')
  await page.getByRole('button', { name: 'Log in' }).click()

  await expect(page.getByText('Invalid username or password.')).toBeVisible()
  await expect(page).toHaveURL(/\/login$/)
})

test('a session survives a page reload (localStorage-backed token)', async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Username').fill('marta')
  await page.getByLabel('Password').fill('agentic-demo-2026')
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)

  await page.reload()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expect(page.getByRole('heading', { name: 'Meridian Logistics' })).toBeVisible()
})

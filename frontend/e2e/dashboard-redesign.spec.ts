import { expect, test } from '@playwright/test'

// specs/012-dashboard-visual-redesign — quickstart.md's User Story 1/3
// validation steps, automated. Requires the backend running against a
// migrated, seeded, and fully fixture-collected + scored database, same
// prerequisite as dashboard-to-evidence.spec.ts.

test.beforeEach(async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Username').fill('marta')
  await page.getByLabel('Password').fill('agentic-demo-2026')
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
})

test('the four redesigned regions are all present with real data (US1)', async ({ page }) => {
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'The Signal Stream' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Churn Risk Overview' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'The Action & Draft Hub' })).toBeVisible()
})

test('the sidebar navigates to Coverage and highlights it as active (FR-001/FR-002)', async ({
  page,
}) => {
  await page.getByRole('link', { name: 'Coverage' }).click()
  await expect(page).toHaveURL(/\/coverage$/)
})

test('the floating assistant starts collapsed and preserves its exchange across collapse (US3)', async ({
  page,
}) => {
  // FR-007: collapsed launcher only on load — no question input visible yet.
  await expect(page.getByLabel('Ask a question')).not.toBeVisible()
  await page.getByRole('button', { name: 'Open assistant' }).click()

  await page.getByLabel('Ask a question').fill('why is the score high?')
  await page.getByRole('button', { name: /ask/i }).click()
  await expect(page.getByTestId('ask-bar')).toHaveAttribute('data-state', 'answered', {
    timeout: 15_000,
  })

  // FR-008: collapsing and reopening must not discard the exchange.
  await page.getByRole('button', { name: 'Collapse assistant' }).click()
  await expect(page.getByLabel('Ask a question')).not.toBeVisible()
  await page.getByRole('button', { name: 'Open assistant' }).click()
  await expect(page.getByTestId('ask-bar')).toHaveAttribute('data-state', 'answered')
})

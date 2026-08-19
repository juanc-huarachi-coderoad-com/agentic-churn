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

// specs/016-dashboard-mockup-v2-refinement (FR-004, SC-007) supersedes the
// floating, collapse-by-default launcher this test used to cover — the
// Assistant is now a permanently docked, already-expanded panel in column 1.
test('the docked assistant is already expanded and usable with zero clicks, and keeps its exchange (FR-004)', async ({
  page,
}) => {
  // No launcher anywhere — ready to accept a message immediately on load.
  await expect(page.getByRole('button', { name: 'Open assistant' })).not.toBeVisible()
  await expect(page.getByLabel('Ask a question')).toBeVisible()

  await page.getByLabel('Ask a question').fill('why is the score high?')
  await page.getByRole('button', { name: /ask/i }).click()
  await expect(page.getByTestId('ask-bar')).toHaveAttribute('data-state', 'answered', {
    timeout: 15_000,
  })

  // Interacting elsewhere on the dashboard must never reset the exchange —
  // there is no collapse state left to reset it (Acceptance Scenario 2).
  await page.getByRole('heading', { name: 'The Signal Stream' }).click()
  await expect(page.getByTestId('ask-bar')).toHaveAttribute('data-state', 'answered')
})

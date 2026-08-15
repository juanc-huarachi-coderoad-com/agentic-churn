import { expect, test } from '@playwright/test'

// Requires the backend running against a migrated, seeded, and fully
// fixture-collected + scored database (specs/006-dashboard-evidence-trace/
// quickstart.md's Prerequisites) — at least one real, validated
// score_contributions row must exist for this spec's click-throughs to have
// something real to open.

test.beforeEach(async ({ page }) => {
  await page.goto('/login')
  await page.getByLabel('Username').fill('marta')
  await page.getByLabel('Password').fill('agentic-demo-2026')
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
})

test('clicking a contribution bar opens the evidence panel with real evidence', async ({
  page,
}) => {
  const bar = page.getByRole('button', { name: /broken response promise/i }).first()
  await bar.click()

  const panel = page.getByRole('dialog', { name: 'Evidence trace' })
  await expect(panel).toBeVisible()
  await expect(panel.getByText(/promised business hours/i)).toBeVisible()
  await expect(panel.getByText(/points total/)).toBeVisible()
})

test('clicking a pulse event opens the evidence panel with the real quoted message', async ({
  page,
}) => {
  const event = page.getByText('“Slow API response”')
  await event.click()

  const panel = page.getByRole('dialog', { name: 'Evidence trace' })
  await expect(panel).toBeVisible()
  await expect(panel.getByText('“Slow API response”')).toBeVisible()
})

test('clicking the score opens the evidence panel for its largest contributor', async ({
  page,
}) => {
  const score = page.getByRole('button', { name: 'Score detail' })
  await score.click()

  const panel = page.getByRole('dialog', { name: 'Evidence trace' })
  await expect(panel).toBeVisible()

  await panel.getByText('Close').click()
  await expect(panel).not.toBeVisible()
})

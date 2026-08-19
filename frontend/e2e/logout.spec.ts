import { expect, test } from '@playwright/test'

// Business-critical, security-relevant path (constitution P11 "business-critical flows
// get end-to-end coverage") — logout must actually revoke the token and block back
// navigation, not just clear local UI state. Requires the backend running against a
// migrated + seeded database, same as login-to-dashboard.spec.ts.

async function login(page: import('@playwright/test').Page) {
  await page.goto('/login')
  await page.getByLabel('Username').fill('marta')
  await page.getByLabel('Password').fill('agentic-demo-2026')
  await page.getByRole('button', { name: 'Log in' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

test('logging out from the account menu revokes the session and returns to /login', async ({
  page,
}) => {
  await login(page)

  await page.getByRole('button', { name: /account/i }).click()
  await page.getByRole('menuitem', { name: 'Log out' }).click()

  await expect(page).toHaveURL(/\/login$/)

  // Back navigation must not restore access to protected content (FR-004, SC-005).
  await page.goBack()
  await expect(page).toHaveURL(/\/login$/)
})

test('clicking outside the account menu closes it without logging out', async ({ page }) => {
  await login(page)

  await page.getByRole('button', { name: /account/i }).click()
  await expect(page.getByRole('menuitem', { name: 'Log out' })).toBeVisible()

  await page.mouse.click(10, 10)
  await expect(page.getByRole('menuitem', { name: 'Log out' })).not.toBeVisible()
  await expect(page).toHaveURL(/\/dashboard$/)
})

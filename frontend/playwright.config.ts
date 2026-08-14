import { defineConfig, devices } from '@playwright/test'

// Business-critical-workflow E2E coverage (constitution P11) — no specs exist yet in
// Project Foundation; this config exists so later phases add tests into an already-wired
// harness instead of building one from scratch (mirrors backend/tests/strategy.md's
// scaffold-before-content approach for this feature, spec.md User Story 3).
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'pnpm dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
})

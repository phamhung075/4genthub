import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright config for the browser checks of the deployed frontend (seat: fe-dev).
 *
 * baseURL comes from E2E_BASE_URL, and the default is the deployed app. A local
 * rigd check points it at the vite dev server (http://localhost:3800), whose
 * /api and /ws proxy to the API on :8000 - see vite.config.ts, where the socket
 * rides the proxy because the app derives its URL from the page origin in dev.
 *
 * One worker, no retries, no watch: a failing run should say what it saw the
 * first time rather than paper over a race. Traces and screenshots stay in
 * test-results/ (gitignored) and are looked at before they are attached.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 0,
  forbidOnly: !!process.env.CI,
  reporter: [['list']],
  timeout: 60_000,
  expect: { timeout: 15_000 },
  outputDir: 'test-results',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'https://www.4genthub.com',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
})
